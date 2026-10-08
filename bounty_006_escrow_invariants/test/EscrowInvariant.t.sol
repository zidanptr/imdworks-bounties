// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/Escrow.sol";

/**
 * @title EscrowInvariantTest
 * @notice Foundry invariant tests for escrow contract
 * @dev Tests:
 *   1. Balance invariant: balance == deposits - releases
 *   2. Access control: only payer can release
 *   3. Approval requirement: no release without approval
 */
contract EscrowHandler is Test {
    SimpleEscrow escrow;
    address payer;
    address payee;
    
    uint256 public totalDeposited;
    uint256 public totalReleased;
    
    constructor(address _escrow, address _payer, address _payee) {
        escrow = SimpleEscrow(_escrow);
        payer = _payer;
        payee = _payee;
    }
    
    function deposit(uint256 amount) external {
        amount = bound(amount, 0, 100 ether);
        if (amount == 0) return;
        
        vm.prank(payer);
        escrow.deposit{value: amount}();
        totalDeposited += amount;
    }
    
    function approve() external {
        vm.prank(payee);
        escrow.approve();
    }
    
    function release(uint256 amount) external {
        // Only release if approved
        try escrow.approved() returns (bool isApproved) {
            if (!isApproved) return;
        } catch {
            return;
        }
        
        uint256 available = totalDeposited - totalReleased;
        amount = bound(amount, 0, available);
        if (amount == 0) return;
        
        vm.prank(payer);
        try escrow.release(amount) {
            totalReleased += amount;
        } catch {
            // Release failed (e.g., insufficient balance)
        }
    }
    
    function refund() external {
        uint256 available = totalDeposited - totalReleased;
        if (available == 0) return;
        
        vm.prank(payer);
        try escrow.refund() {
            totalReleased += available;
        } catch {
            // Refund failed
        }
    }
}

contract EscrowInvariantTest is Test {
    SimpleEscrow escrow;
    EscrowHandler handler;
    
    address payer = address(0x1);
    address payee = address(0x2);
    
    function setUp() public {
        vm.deal(payer, 1000 ether);
        vm.deal(payee, 1 ether);
        
        escrow = new SimpleEscrow(payee);
        handler = new EscrowHandler(address(escrow), payer, payee);
        
        vm.label(payer, "payer");
        vm.label(payee, "payee");
        vm.label(address(escrow), "escrow");
    }
    
    /**
     * @notice Invariant 1: Balance always equals deposits minus releases
     */
    function invariant_balance() public view {
        uint256 balance = address(escrow).balance;
        uint256 expected = escrow.totalDeposited() - escrow.totalReleased();
        
        assertEq(balance, expected, "Balance invariant violated");
    }
    
    /**
     * @notice Invariant 2: Only payer can release
     */
    function invariant_only_payer_can_release() public {
        // Setup fresh escrow
        SimpleEscrow testEscrow = new SimpleEscrow{value: 1 ether}(payee);
        
        // Approve
        vm.prank(payee);
        testEscrow.approve();
        
        // Non-payer tries to release
        vm.prank(payee);
        vm.expectRevert(SimpleEscrow.OnlyPayer.selector);
        testEscrow.release(0.5 ether);
        
        // Payer can release
        vm.prank(payer);
        testEscrow.release(0.5 ether);
        
        assertEq(testEscrow.totalReleased(), 0.5 ether);
    }
    
    /**
     * @notice Invariant 3: No release without approval
     */
    function invariant_no_release_without_approval() public {
        SimpleEscrow testEscrow = new SimpleEscrow{value: 1 ether}(payee);
        
        // Payer tries to release without approval
        vm.prank(payer);
        vm.expectRevert(SimpleEscrow.NotApproved.selector);
        testEscrow.release(0.5 ether);
        
        // After approval, release works
        vm.prank(payee);
        testEscrow.approve();
        
        vm.prank(payer);
        testEscrow.release(0.5 ether);
        
        assertEq(testEscrow.totalReleased(), 0.5 ether);
    }
}

/**
 * @title Fuzz tests for escrow
 */
contract EscrowFuzzTest is Test {
    SimpleEscrow escrow;
    address payer = address(0x1);
    address payee = address(0x2);
    
    function setUp() public {
        vm.deal(payer, 1000 ether);
        escrow = new SimpleEscrow(payee);
    }
    
    function testFuzz_Deposit(uint256 amount) public {
        amount = bound(amount, 1, 100 ether);
        
        vm.prank(payer);
        escrow.deposit{value: amount}();
        
        assertEq(escrow.totalDeposited(), amount);
        assertEq(address(escrow).balance, amount);
    }
    
    function testFuzz_Release(uint256 depositAmount, uint256 releaseAmount) public {
        depositAmount = bound(depositAmount, 1, 100 ether);
        
        vm.prank(payer);
        escrow.deposit{value: depositAmount}();
        
        vm.prank(payee);
        escrow.approve();
        
        releaseAmount = bound(releaseAmount, 0, depositAmount);
        
        if (releaseAmount > 0) {
            vm.prank(payer);
            escrow.release(releaseAmount);
            
            assertEq(escrow.totalReleased(), releaseAmount);
        }
        
        // Balance invariant
        uint256 expected = depositAmount - releaseAmount;
        assertEq(address(escrow).balance, expected);
    }
    
    function testFuzz_MultipleDeposits(uint256[] calldata amounts) public {
        vm.assume(amounts.length <= 10);
        
        uint256 total;
        for (uint256 i = 0; i < amounts.length; i++) {
            uint256 amount = bound(amounts[i], 1, 10 ether);
            vm.prank(payer);
            escrow.deposit{value: amount}();
            total += amount;
        }
        
        assertEq(escrow.totalDeposited(), total);
        assertEq(address(escrow).balance, total);
    }
    
    function testFuzz_InvariantAfterRandomOps(uint8 ops, bytes32 seed) public {
        uint256 deposited;
        uint256 released;
        bool approved;
        
        for (uint256 i = 0; i < ops % 20; i++) {
            uint256 action = uint256(keccak256(abi.encode(seed, i))) % 4;
            
            if (action == 0) {
                // Deposit
                uint256 amount = uint256(keccak256(abi.encode(seed, i, "deposit"))) % 10 ether;
                if (amount > 0) {
                    vm.prank(payer);
                    escrow.deposit{value: amount}();
                    deposited += amount;
                }
            } else if (action == 1) {
                // Approve
                if (!approved) {
                    vm.prank(payee);
                    escrow.approve();
                    approved = true;
                }
            } else if (action == 2) {
                // Release
                if (approved && deposited > released) {
                    uint256 maxRelease = deposited - released;
                    uint256 amount = uint256(keccak256(abi.encode(seed, i, "release"))) % maxRelease;
                    if (amount > 0) {
                        vm.prank(payer);
                        try escrow.release(amount) {
                            released += amount;
                        } catch {}
                    }
                }
            } else {
                // Refund
                if (deposited > released) {
                    vm.prank(payer);
                    try escrow.refund() {
                        released = deposited;
                    } catch {}
                }
            }
            
            // Check invariant after each operation
            assertEq(address(escrow).balance, deposited - released);
        }
    }
}

/**
 * @title Edge case tests
 */
contract EscrowEdgeCaseTest is Test {
    SimpleEscrow escrow;
    address payer = address(0x1);
    address payee = address(0x2);
    
    function setUp() public {
        vm.deal(payer, 100 ether);
    }
    
    function test_ZeroDeposit() public {
        escrow = new SimpleEscrow(payee);
        
        vm.prank(payer);
        escrow.deposit{value: 0}();
        
        assertEq(escrow.totalDeposited(), 0);
    }
    
    function test_ReleaseExactBalance() public {
        escrow = new SimpleEscrow{value: 1 ether}(payee);
        
        vm.prank(payee);
        escrow.approve();
        
        vm.prank(payer);
        escrow.release(1 ether);
        
        assertEq(address(escrow).balance, 0);
        assertEq(escrow.totalReleased(), 1 ether);
    }
    
    function test_MultiplePartialReleases() public {
        escrow = new SimpleEscrow{value: 10 ether}(payee);
        
        vm.prank(payee);
        escrow.approve();
        
        for (uint256 i = 0; i < 10; i++) {
            vm.prank(payer);
            escrow.release(1 ether);
        }
        
        assertEq(escrow.totalReleased(), 10 ether);
        assertEq(address(escrow).balance, 0);
    }
    
    function test_RefundCancelsEscrow() public {
        escrow = new SimpleEscrow{value: 5 ether}(payee);
        
        vm.prank(payee);
        escrow.approve();
        
        vm.prank(payer);
        escrow.refund();
        
        assertEq(escrow.totalReleased(), 5 ether);
        assertEq(address(escrow).balance, 0);
    }
}
