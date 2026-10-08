// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title RestrictedToken
 * @notice Mock ERC20 with configurable transfer restrictions
 * @dev For testing purposes - DO NOT USE IN PRODUCTION
 */
contract RestrictedToken is ERC20, Ownable {
    // Blacklist
    mapping(address => bool) public isBlacklisted;
    
    // Whitelist (if enabled, only whitelisted can transfer)
    mapping(address => bool) public isWhitelisted;
    bool public whitelistEnabled;
    
    // Transfer limits
    uint256 public maxTransferAmount;
    bool public transferLimitEnabled;
    
    // Cooldown
    uint256 public cooldownPeriod;
    mapping(address => uint256) public lastTransferTime;
    bool public cooldownEnabled;
    
    // Pause
    bool public paused;
    
    // Events
    event Blacklisted(address indexed account, bool status);
    event Whitelisted(address indexed account, bool status);
    event WhitelistEnabled(bool enabled);
    event TransferLimitSet(uint256 maxAmount);
    event CooldownSet(uint256 period);
    event Paused(bool status);
    
    // Errors
    error BlacklistedAccount(address account);
    error NotWhitelisted(address account);
    error TransferLimitExceeded(uint256 amount, uint256 max);
    error CooldownNotMet(address account, uint256 timeRemaining);
    error TokenPaused();
    error InvalidAmount();
    error InvalidCooldown();
    
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply
    ) ERC20(name, symbol) Ownable(msg.sender) {
        _mint(msg.sender, initialSupply);
        maxTransferAmount = type(uint256).max;
        cooldownPeriod = 0;
    }
    
    // ============ Admin Functions ============
    
    function setBlacklist(address account, bool status) external onlyOwner {
        isBlacklisted[account] = status;
        emit Blacklisted(account, status);
    }
    
    function setWhitelist(address account, bool status) external onlyOwner {
        isWhitelisted[account] = status;
        emit Whitelisted(account, status);
    }
    
    function enableWhitelist(bool enabled) external onlyOwner {
        whitelistEnabled = enabled;
        emit WhitelistEnabled(enabled);
    }
    
    function setTransferLimit(uint256 maxAmount) external onlyOwner {
        maxTransferAmount = maxAmount;
        transferLimitEnabled = maxAmount < type(uint256).max;
        emit TransferLimitSet(maxAmount);
    }
    
    function setCooldown(uint256 period) external onlyOwner {
        if (period > 365 days) revert InvalidCooldown();
        cooldownPeriod = period;
        cooldownEnabled = period > 0;
        emit CooldownSet(period);
    }
    
    function setPaused(bool status) external onlyOwner {
        paused = status;
        emit Paused(status);
    }
    
    // ============ Transfer Override ============
    
    function _update(address from, address to, uint256 amount) internal virtual override {
        // Skip checks for minting/burning
        if (from != address(0) && to != address(0)) {
            // Pause check
            if (paused) revert TokenPaused();
            
            // Blacklist check
            if (isBlacklisted[from]) revert BlacklistedAccount(from);
            if (isBlacklisted[to]) revert BlacklistedAccount(to);
            
            // Whitelist check
            if (whitelistEnabled) {
                if (!isWhitelisted[from]) revert NotWhitelisted(from);
                if (!isWhitelisted[to]) revert NotWhitelisted(to);
            }
            
            // Transfer limit check
            if (transferLimitEnabled && amount > maxTransferAmount) {
                revert TransferLimitExceeded(amount, maxTransferAmount);
            }
            
            // Cooldown check
            if (cooldownEnabled && from != address(0)) {
                uint256 timeSinceLastTransfer = block.timestamp - lastTransferTime[from];
                if (timeSinceLastTransfer < cooldownPeriod) {
                    revert CooldownNotMet(from, cooldownPeriod - timeSinceLastTransfer);
                }
                lastTransferTime[from] = block.timestamp;
            }
        }
        
        super._update(from, to, amount);
    }
    
    // ============ View Functions ============
    
    function getTimeUntilNextTransfer(address account) external view returns (uint256) {
        if (!cooldownEnabled) return 0;
        uint256 timeSinceLast = block.timestamp - lastTransferTime[account];
        if (timeSinceLast >= cooldownPeriod) return 0;
        return cooldownPeriod - timeSinceLast;
    }
    
    function canTransfer(address from, address to, uint256 amount) external view returns (bool, string memory) {
        if (paused) return (false, "Token paused");
        if (isBlacklisted[from]) return (false, "Sender blacklisted");
        if (isBlacklisted[to]) return (false, "Recipient blacklisted");
        if (whitelistEnabled && !isWhitelisted[from]) return (false, "Sender not whitelisted");
        if (whitelistEnabled && !isWhitelisted[to]) return (false, "Recipient not whitelisted");
        if (transferLimitEnabled && amount > maxTransferAmount) return (false, "Transfer limit exceeded");
        if (cooldownEnabled) {
            uint256 timeSince = block.timestamp - lastTransferTime[from];
            if (timeSince < cooldownPeriod) return (false, "Cooldown not met");
        }
        return (true, "");
    }
}
