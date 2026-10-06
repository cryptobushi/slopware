// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console} from "forge-std/Script.sol";
import {Slopware} from "../src/Slopware.sol";

/// @notice Deploys SLOPWARE. Immutable except for `price`, which only the artist may change.
///
/// Environment:
///   ARTIST     receives payments and may set the price      (default: deployer)
///   PRICE  initial price in wei                      (default 0.0003 ether)
contract Deploy is Script {
    function run() external returns (Slopware s) {
        uint256 fee = vm.envOr("PRICE", uint256(0.0003 ether));
        vm.startBroadcast();
        address artist = vm.envOr("ARTIST", msg.sender);
        s = new Slopware(artist, fee);
        vm.stopBroadcast();
        console.log("SLOPWARE       ", address(s));
        console.log("artist         ", artist);
        console.log("price (wei)    ", fee);
        console.log("DEPLOY_GAS     ", s.DEPLOY_GAS());
        console.log("chain id       ", block.chainid);
    }
}
