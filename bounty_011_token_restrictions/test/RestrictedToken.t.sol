// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/RestrictedToken.sol";

contract RestrictedTokenTest is Test {
    RestrictedToken token;
    address owner = address(0x1);
    address alice = address(0x2);
    address bob = address(0x3);
    address charlie = address(0x4);
    
    function setUp() public {
        vm.prank(owner);
        token = new RestrictedToken("Restricted Token", "RSTR", 1000000 * 10**18);
        
        vm.label(owner, "owner");
        vm.label(alice, "alice");
        vm.label(bob, "bob");
        vm.label(charlie, "charlie");
        
        // Distribute tokens
        vm.prank(owner);
        token.transfer(alice, 10000 * 10**18);
        vm.prank(owner);
        token.transfer(bob, 10000 * 10**18);
    }
    
    // ============ Blacklist Tests ============
    
    function test_BlacklistPreventsTransfer() public {
        vm.prank(owner);
        token.setBlacklist(alice, true);
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(RestrictedToken.BlacklistedAccount.selector, alice));
        token.transfer(bob, 100 * 10**18);
    }
    
    function test_BlacklistPreventsReceiving() public {
        vm.prank(owner);
        token.setBlacklist(bob, true);
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(RestrictedToken.BlacklistedAccount.selector, bob));
        token.transfer(bob, 100 * 10**18);
    }
    
    function test_UnblacklistAllowsTransfer() public {
        vm.startPrank(owner);
        token.setBlacklist(alice, true);
        token.setBlacklist(alice, false);
        vm.stopPrank();
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        assertEq(token.balanceOf(bob), 10100 * 10**18);
    }
    
    // ============ Whitelist Tests ============
    
    function test_WhitelistOnlyAllowsWhitelisted() public {
        vm.startPrank(owner);
        token.enableWhitelist(true);
        token.setWhitelist(alice, true);
        token.setWhitelist(bob, true);
        vm.stopPrank();
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        assertEq(token.balanceOf(bob), 10100 * 10**18);
    }
    
    function test_NonWhitelistedCannotTransfer() public {
        vm.prank(owner);
        token.enableWhitelist(true);
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(RestrictedToken.NotWhitelisted.selector, alice));
        token.transfer(bob, 100 * 10**18);
    }
    
    function test_NonWhitelistedCannotReceive() public {
        vm.startPrank(owner);
        token.enableWhitelist(true);
        token.setWhitelist(alice, true);
        vm.stopPrank();
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(RestrictedToken.NotWhitelisted.selector, bob));
        token.transfer(bob, 100 * 10**18);
    }
    
    // ============ Transfer Limit Tests ============
    
    function test_TransferLimitEnforced() public {
        uint256 limit = 1000 * 10**18;
        vm.prank(owner);
        token.setTransferLimit(limit);
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            RestrictedToken.TransferLimitExceeded.selector,
            2000 * 10**18,
            limit
        ));
        token.transfer(bob, 2000 * 10**18);
    }
    
    function test_TransferWithinLimitSucceeds() public {
        uint256 limit = 1000 * 10**18;
        vm.prank(owner);
        token.setTransferLimit(limit);
        
        vm.prank(alice);
        token.transfer(bob, 500 * 10**18);
        
        assertEq(token.balanceOf(bob), 10500 * 10**18);
    }
    
    function test_TransferAtLimitSucceeds() public {
        uint256 limit = 1000 * 10**18;
        vm.prank(owner);
        token.setTransferLimit(limit);
        
        vm.prank(alice);
        token.transfer(bob, limit);
        
        assertEq(token.balanceOf(bob), 11000 * 10**18);
    }
    
    // ============ Cooldown Tests ============
    
    function test_CooldownPreventsRapidTransfer() public {
        vm.prank(owner);
        token.setCooldown(1 hours);
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        vm.warp(block.timestamp + 30 minutes);
        
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            RestrictedToken.CooldownNotMet.selector,
            alice,
            30 minutes
        ));
        token.transfer(charlie, 100 * 10**18);
    }
    
    function test_CooldownAllowsTransferAfterPeriod() public {
        vm.prank(owner);
        token.setCooldown(1 hours);
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        vm.warp(block.timestamp + 1 hours);
        
        vm.prank(alice);
        token.transfer(charlie, 100 * 10**18);
        
        assertEq(token.balanceOf(charlie), 100 * 10**18);
    }
    
    function test_GetTimeUntilNextTransfer() public {
        vm.prank(owner);
        token.setCooldown(1 hours);
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        vm.warp(block.timestamp + 30 minutes);
        
        uint256 remaining = token.getTimeUntilNextTransfer(alice);
        assertEq(remaining, 30 minutes);
    }
    
    // ============ Pause Tests ============
    
    function test_PauseBlocksTransfers() public {
        vm.prank(owner);
        token.setPaused(true);
        
        vm.prank(alice);
        vm.expectRevert(RestrictedToken.TokenPaused.selector);
        token.transfer(bob, 100 * 10**18);
    }
    
    function test_UnpauseAllowsTransfers() public {
        vm.startPrank(owner);
        token.setPaused(true);
        token.setPaused(false);
        vm.stopPrank();
        
        vm.prank(alice);
        token.transfer(bob, 100 * 10**18);
        
        assertEq(token.balanceOf(bob), 10100 * 10**18);
    }
    
    // ============ Combined Restrictions Tests ============
    
    function test_MultipleRestrictionsBlacklistPriority() public {
        vm.startPrank(owner);
        token.setTransferLimit(500 * 10**18);
        token.setCooldown(1 hours);
        token.setBlacklist(alice, true);
        vm.stopPrank();
        
        // Should revert with blacklist error, not transfer limit or cooldown
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(RestrictedToken.BlacklistedAccount.selector, alice));
        token.transfer(bob, 100 * 10**18);
    }
    
    function test_MultipleRestrictionsPausePriority() public {
        vm.startPrank(owner);
        token.setTransferLimit(500 * 10**18);
        token.setBlacklist(alice, true);
        token.setPaused(true);
        vm.stopPrank();
        
        // Should revert with pause error first
        vm.prank(alice);
        vm.expectRevert(RestrictedToken.TokenPaused.selector);
        token.transfer(bob, 100 * 10**18);
    }
    
    // ============ View Function Tests ============
    
    function test_CanTransferReturnsTrue() public {
        (bool canTransfer, string memory reason) = token.canTransfer(alice, bob, 100 * 10**18);
        assertTrue(canTransfer);
        assertEq(reason, "");
    }
    
    function test_CanTransferReturnsFalse() public {
        vm.prank(owner);
        token.setBlacklist(alice, true);
        
        (bool canTransfer, string memory reason) = token.canTransfer(alice, bob, 100 * 10**18);
        assertFalse(canTransfer);
        assertTrue(bytes(reason).length > 0);
    }
    
    // ============ Fuzz Tests ============
    
    function testFuzz_TransferAmount(uint256 amount) public {
        uint256 aliceBalance = token.balanceOf(alice);
        amount = bound(amount, 0, aliceBalance);
        
        vm.prank(alice);
        token.transfer(bob, amount);
        
        assertEq(token.balanceOf(alice), aliceBalance - amount);
        assertEq(token.balanceOf(bob), 10000 * 10**18 + amount);
    }
    
    function testFuzz_TransferLimit(uint256 limit, uint256 amount) public {
        limit = bound(limit, 1, 1000000 * 10**18);
        amount = bound(amount, 0, 20000 * 10**18);
        
        vm.prank(owner);
        token.setTransferLimit(limit);
        
        if (amount <= limit && amount <= token.balanceOf(alice)) {
            vm.prank(alice);
            token.transfer(bob, amount);
            assertEq(token.balanceOf(bob), 10000 * 10**18 + amount);
        } else if (amount > limit) {
            vm.prank(alice);
            vm.expectRevert();
            token.transfer(bob, amount);
        }
    }
    
    // ============ Edge Cases ============
    
    function test_TransferZeroAmount() public {
        vm.prank(alice);
        token.transfer(bob, 0);
        
        assertEq(token.balanceOf(alice), 10000 * 10**18);
        assertEq(token.balanceOf(bob), 10000 * 10**18);
    }
    
    function test_TransferToSelf() public {
        vm.prank(alice);
        token.transfer(alice, 100 * 10**18);
        
        assertEq(token.balanceOf(alice), 10000 * 10**18);
    }
    
    function test_ApproveAndTransferFrom() public {
        vm.prank(alice);
        token.approve(bob, 1000 * 10**18);
        
        vm.prank(bob);
        token.transferFrom(alice, charlie, 500 * 10**18);
        
        assertEq(token.balanceOf(charlie), 500 * 10**18);
    }
}
