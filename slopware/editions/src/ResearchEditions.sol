// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@manifoldxyz/creator-core-solidity/contracts/ERC721Creator.sol";

/// Manifold's ERC721Creator, unchanged, under the name used for SLOPWARE research editions.
contract ResearchEditions is ERC721Creator {
    constructor(string memory name_, string memory symbol_) ERC721Creator(name_, symbol_) {}
}
