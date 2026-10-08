// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title SimpleEscrow
 * @notice Escrow contract with invariant guarantees
 * @dev Invariants:
 *   1. balance == totalDeposited - totalReleased
 *   2. Only payer can release funds
 *   3. No partial release without payee approval
 */
contract SimpleEscrow {
    address public immutable payer;
    address public payee;
    uint256 public totalDeposited;
    uint256 public totalReleased;
    bool public approved;
    
    event Deposited(address indexed from, uint256 amount);
    event Approved(address indexed payee);
    event Released(address indexed to, uint256 amount);
    event Refunded(address indexed to, uint256 amount);
    
    error OnlyPayer();
    error OnlyPayee();
    error NotApproved();
    error InsufficientBalance();
    error ZeroAddress();
    error TransferFailed();
    
    constructor(address _payee) payable {
        if (_payee == address(0)) revert ZeroAddress();
        payer = msg.sender;
        payee = _payee;
        if (msg.value > 0) {
            totalDeposited += msg.value;
            emit Deposited(msg.sender, msg.value);
        }
    }
    
    /**
     * @notice Deposit funds into escrow
     */
    function deposit() external payable {
        if (msg.value == 0) return;
        totalDeposited += msg.value;
        emit Deposited(msg.sender, msg.value);
    }
    
    /**
     * @notice Payee approves release of funds
     */
    function approve() external {
        if (msg.sender != payee) revert OnlyPayee();
        approved = true;
        emit Approved(payee);
    }
    
    /**
     * @notice Release funds to payee (only after approval)
     * @param amount Amount to release
     */
    function release(uint256 amount) external {
        if (msg.sender != payer) revert OnlyPayer();
        if (!approved) revert NotApproved();
        
        uint256 available = totalDeposited - totalReleased;
        if (amount > available) revert InsufficientBalance();
        
        totalReleased += amount;
        
        (bool success, ) = payee.call{value: amount}("");
        if (!success) revert TransferFailed();
        
        emit Released(payee, amount);
    }
    
    /**
     * @notice Refund remaining funds to payer
     */
    function refund() external {
        if (msg.sender != payer) revert OnlyPayer();
        
        uint256 available = totalDeposited - totalReleased;
        if (available == 0) return;
        
        totalReleased += available;
        
        (bool success, ) = payer.call{value: available}("");
        if (!success) revert TransferFailed();
        
        emit Refunded(payer, available);
    }
    
    /**
     * @notice Get available balance
     */
    function getAvailableBalance() external view returns (uint256) {
        return totalDeposited - totalReleased;
    }
    
    /**
     * @notice Invariant check: balance should always equal deposits - releases
     */
    function invariant() external view returns (bool) {
        return address(this).balance == totalDeposited - totalReleased;
    }
}
