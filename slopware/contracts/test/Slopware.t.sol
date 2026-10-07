// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Test, Vm} from "forge-std/Test.sol";
import {Slopware} from "../src/Slopware.sol";
import {Base64} from "solady/utils/Base64.sol";

/// @dev Exposes the deployment primitive so a large corpus can be pushed through it directly.
contract SlopwareHarness is Slopware {
    constructor(address a, uint256 f) Slopware(a, f) {}

    function placeBytecode(bytes memory bytecode) external returns (address) {
        return _place(bytecode);
    }
}

/// @dev A installer that is a contract and tries to re-enter on every opportunity.
contract Reentrant {
    Slopware s;

    constructor(Slopware s_) {
        s = s_;
    }

    function request() external payable returns (uint256) {
        return s.install{value: msg.value}();
    }

    receive() external payable {
        // if anything ever pays us during a installation, try to re-enter
        try s.install{value: 0}() {} catch {}
    }

    function onERC721Received(address, address, uint256, bytes calldata) external returns (bytes4) {
        try s.install{value: 0}() {} catch {}
        return this.onERC721Received.selector;
    }
}

contract SlopwareTest is Test {
    uint256 constant FEE = 0.0003 ether;
    address artist = address(0xA27);
    address alice = address(0xA11CE);
    address bob = address(0xB0B);
    SlopwareHarness w;

    event Installed(uint256 indexed release, address indexed installer, address indexed program, bytes32 checksum, bytes bytecode);
    event Rejected(uint256 indexed release, address indexed installer, bytes32 checksum, bytes bytecode, bytes32 reason);

    function setUp() public {
        vm.roll(20_000_000);
        w = new SlopwareHarness(artist, FEE);
        vm.deal(alice, 10 ether);
        vm.deal(bob, 10 ether);
    }

    // ------------------------------------------------------------ helpers

    function _request(address who) internal returns (uint256 id) {
        vm.prank(who);
        id = w.install{value: FEE}();
    }

    function _finalize(uint256 id) internal {
        Slopware.Software memory s = w.software(id);
        vm.roll(uint256(s.requestedAt) + 2);
        w.complete(id);
    }

    function _expectedBytecode(uint256 id) internal view returns (bytes memory) {
        Slopware.Software memory s = w.software(id);
        bytes32 e = blockhash(uint256(s.requestedAt) + 1);
        return abi.encodePacked(keccak256(abi.encodePacked(e, id, uint8(0))), keccak256(abi.encodePacked(e, id, uint8(1))));
    }

    /// @dev find a block hash whose derived bytecode begins with 0xEF, so Ethereum must refuse it.
    ///      vm.setBlockhash only accepts blocks at or below the current one, so roll past it first.
    function _forceRejection(uint256 id) internal {
        Slopware.Software memory s = w.software(id);
        uint256 eb = uint256(s.requestedAt) + 1;
        vm.roll(eb + 1);
        for (uint256 k = 1;; k++) {
            bytes32 h = keccak256(abi.encodePacked("rejection", k));
            bytes32 first = keccak256(abi.encodePacked(h, id, uint8(0)));
            if (first[0] == 0xef) {
                vm.setBlockhash(eb, h);
                return;
            }
        }
    }

    // ------------------------------------------------------------ 1–3: the invariant

    function test_install_codeIsExactlyTheBytecode() public {
        uint256 id = _request(alice);
        vm.roll(w.software(id).requestedAt + 2);
        bytes memory expected = _expectedBytecode(id);
        vm.expectEmit(true, true, false, false);
        emit Installed(id, alice, address(0), bytes32(0), "");
        w.complete(id);

        Slopware.Software memory s = w.software(id);
        assertEq(uint8(s.status), uint8(Slopware.Status.Installed));
        assertEq(s.program.code.length, 64, "runtime length");
        assertEq(keccak256(s.program.code), keccak256(expected), "runtime hash");
        assertEq(s.program.code, expected, "runtime bytes");
        assertEq(s.checksum, keccak256(expected));
        assertEq(w.bytecodeOf(id), expected);
        assertEq(w.releaseOf(s.program), id);
        assertEq(w.installed(), 1);
        assertEq(w.ownerOf(id), alice);
        assertEq(s.installer, alice);
    }

    // ------------------------------------------------------------ 4: corpus, zero silent mutation

    function test_corpus_deterministic_noMutation() public {
        uint256 n = 3_000;
        uint256 refused;
        for (uint256 i = 0; i < n; i++) {
            bytes memory g = abi.encodePacked(keccak256(abi.encodePacked("corpus", i, uint8(0))), keccak256(abi.encodePacked("corpus", i, uint8(1))));
            address org = w.placeBytecode(g);
            if (g[0] == 0xef) {
                assertEq(org, address(0), "EIP-3541 bytecode must be refused");
                refused++;
            } else {
                assertTrue(org != address(0), "non-EF bytecode must deploy");
                assertEq(org.code.length, 64);
                assertEq(org.code, g, "deployed runtime differs from bytecode");
                assertEq(keccak256(org.code), keccak256(g));
            }
        }
        // ~1/256 of uniformly random first bytes are 0xEF
        assertGt(refused, 0);
        assertLt(refused, n / 64);
    }

    function testFuzz_anyBytecodePlacesUnchangedOrIsRefused(bytes32 a, bytes32 b) public {
        bytes memory g = abi.encodePacked(a, b);
        address org = w.placeBytecode(g);
        if (g[0] == 0xef) assertEq(org, address(0));
        else {
            assertEq(org.code, g);
            assertEq(org.code.length, 64);
        }
    }

    function testFuzz_completeFromAnyEntropy(bytes32 entropy) public {
        vm.assume(entropy != bytes32(0));
        uint256 id = _request(alice);
        uint256 eb = w.software(id).requestedAt + 1;
        vm.roll(eb + 1);
        vm.setBlockhash(eb, entropy);
        w.complete(id);
        Slopware.Software memory s = w.software(id);
        bytes memory g = w.bytecodeOf(id);
        assertEq(g.length, 64);
        if (g[0] == 0xef) assertEq(uint8(s.status), uint8(Slopware.Status.Rejected));
        else {
            assertEq(uint8(s.status), uint8(Slopware.Status.Installed));
            assertEq(s.program.code, g);
        }
    }

    // ------------------------------------------------------------ 5–6: rejection, no reroll

    function test_rejection_recordedNotRerolled() public {
        uint256 id = _request(alice);
        _forceRejection(id);
        bytes memory expected = _expectedBytecode(id);
        assertEq(expected[0], bytes1(0xef));
        vm.expectEmit(true, true, false, true);
        emit Rejected(id, alice, keccak256(expected), expected, bytes32("EIP-3541"));
        w.complete(id);

        Slopware.Software memory s = w.software(id);
        assertEq(uint8(s.status), uint8(Slopware.Status.Rejected));
        assertEq(s.program, address(0));
        assertEq(w.bytecodeOf(id), expected, "the refused bytecode is kept, not replaced");
        assertEq(w.rejected(), 1);
        assertEq(w.ownerOf(id), alice, "the collector keeps the release number");
        // no second attempt is possible
        vm.expectRevert(Slopware.NotInstalling.selector);
        w.complete(id);
    }

    function test_rejection_gasIsBounded() public {
        uint256 id = _request(alice);
        _forceRejection(id);
        uint256 g0 = gasleft();
        w.complete(id);
        uint256 used = g0 - gasleft();
        emit log_named_uint("rejection gas", used);
        assertLt(used, 200_000, "a refusal is recorded, not paid for: no CREATE runs for refused bytecode");
        assertEq(uint8(w.software(id).status), uint8(Slopware.Status.Rejected));
    }


    function test_gasStarvedPlacement_revertsInsteadOfRejection() public {
        uint256 id = _request(alice);
        vm.roll(w.software(id).requestedAt + 2);
        // not enough gas to place the program: the completion must revert, not record a false rejection.
        // CREATE is given all remaining gas, so a shortfall surfaces as an out-of-gas revert (or PlacementFailed)
        (bool ok,) = address(w).call{gas: 60_000}(abi.encodeWithSelector(w.complete.selector, id));
        assertFalse(ok);
        assertEq(uint8(w.software(id).status), uint8(Slopware.Status.Installing), "still requested; can be retried");
        w.complete(id);
        assertEq(uint8(w.software(id).status), uint8(Slopware.Status.Installed));
    }

    // ------------------------------------------------------------ 7–9: numbering, provenance, transfer

    function test_sequentialReleases_andInstallerImmutable() public {
        uint256 a = _request(alice);
        uint256 b = _request(bob);
        uint256 c = _request(alice);
        assertEq(a, 1);
        assertEq(b, 2);
        assertEq(c, 3);
        assertEq(w.releases(), 3);
        _finalize(a);
        _finalize(b);
        _finalize(c);
        vm.prank(alice);
        w.transferFrom(alice, bob, a);
        assertEq(w.ownerOf(a), bob, "owner changes");
        assertEq(w.software(a).installer, alice, "installer never changes");
    }

    // ------------------------------------------------------------ 10–11: once, and only once

    function test_complete_onceAndNotEarly() public {
        uint256 id = _request(alice);
        vm.expectRevert(Slopware.TooSoon.selector);
        w.complete(id); // same block
        vm.roll(block.number + 1);
        vm.expectRevert(Slopware.TooSoon.selector);
        w.complete(id); // entropy block exists but is the current block: its hash is not final
        vm.roll(block.number + 1);
        w.complete(id);
        vm.expectRevert(Slopware.NotInstalling.selector);
        w.complete(id);
    }

    function test_twoInstallsSameBlock_differentBytecode() public {
        uint256 a = _request(alice);
        uint256 b = _request(bob);
        _finalize(a);
        _finalize(b);
        assertTrue(w.software(a).checksum != w.software(b).checksum, "same entropy block, different ids, different bytecodes");
    }

    function test_abandonment_refundNotSubstitution() public {
        uint256 id = _request(alice);
        vm.roll(w.software(id).requestedAt + 1 + 257);
        assertEq(blockhash(w.software(id).requestedAt + 1), bytes32(0));
        w.complete(id);
        Slopware.Software memory s = w.software(id);
        assertEq(uint8(s.status), uint8(Slopware.Status.Abandoned));
        assertEq(w.bytecodeOf(id).length, 0, "no bytecode was produced");
        assertEq(w.refunds(alice), FEE);
        uint256 before = alice.balance;
        vm.prank(alice);
        w.claimRefund();
        assertEq(alice.balance, before + FEE);
        assertEq(w.totalRefundable(), 0);
    }

    // ------------------------------------------------------------ 12–13: fees

    function test_fees_accountingAndAuthorization() public {
        vm.prank(alice);
        vm.expectRevert(Slopware.WrongPrice.selector);
        w.install{value: FEE - 1}();

        _request(alice);
        _request(bob);
        uint256 expired = _request(alice);
        vm.roll(block.number + 300);
        w.complete(expired); // refundable
        assertEq(address(w).balance, 3 * FEE);
        assertEq(w.totalRefundable(), FEE);

        vm.prank(bob);
        w.withdraw(); // anyone may trigger; funds go to the artist
        assertEq(artist.balance, 2 * FEE, "artist gets everything except refunds owed");
        assertEq(address(w).balance, FEE);

        vm.prank(alice);
        vm.expectRevert(Slopware.NotArtist.selector);
        w.setPrice(1);
        vm.prank(artist);
        w.setPrice(1 wei);
        assertEq(w.price(), 1 wei);
    }

    // ------------------------------------------------------------ 14–15: the factory never calls the program

    function test_installerNeverCallsProgram() public {
        // if the factory ever executed the program, this bytecode (INVALID at pc 0) would revert the installation
        uint256 id = _request(alice);
        uint256 eb = w.software(id).requestedAt + 1;
        vm.roll(eb + 1);
        for (uint256 k = 1;; k++) {
            bytes32 h = keccak256(abi.encodePacked("invalid", k));
            if (keccak256(abi.encodePacked(h, id, uint8(0)))[0] == 0xfe) {
                vm.setBlockhash(eb, h);
                break;
            }
        }
        w.complete(id);
        Slopware.Software memory s = w.software(id);
        assertEq(uint8(s.status), uint8(Slopware.Status.Installed));
        assertEq(s.program.code[0], bytes1(0xfe));
        // and the program has no power over the factory: calling it ourselves changes nothing here
        (bool ok,) = s.program.call("");
        assertFalse(ok);
        assertEq(w.releases(), 1);
        assertEq(w.installed(), 1);
    }

    // ------------------------------------------------------------ 16–18: reentrancy, contract callers, receivers

    function test_contractInstaller_noCallbacksNoReentry() public {
        Reentrant r = new Reentrant(w);
        vm.deal(address(r), 1 ether);
        uint256 id = r.request{value: FEE}();
        assertEq(w.ownerOf(id), address(r));
        assertEq(w.releases(), 1, "no re-entered request happened during mint");
        _finalize(id);
        assertEq(w.releases(), 1, "no re-entered request happened during installation");
        assertEq(uint8(w.software(id).status), uint8(Slopware.Status.Installed));
    }

    function test_mintUsesNoReceiverCallback() public {
        // a contract with no onERC721Received at all can still be a installer
        address plain = address(new PlainContract());
        vm.deal(plain, 1 ether);
        vm.prank(plain);
        uint256 id = w.install{value: FEE}();
        assertEq(w.ownerOf(id), plain);
    }

    // ------------------------------------------------------------ metadata

    function test_tokenURI_isFactual() public {
        uint256 id = _request(alice);
        _finalize(id);
        string memory raw = w.tokenURI(id);
        assertTrue(_contains(raw, "data:application/json;base64,"));
        // decode the JSON, then the image inside it; both must be well formed and factual
        string memory uri = string(Base64.decode(_after(raw, "base64,")));
        assertTrue(_contains(uri, '"name":"SLOPWARE 000001"'));
        assertTrue(_contains(uri, '"image":"data:image/svg+xml;base64,'));
        string memory svg = string(Base64.decode(_between(uri, 'svg+xml;base64,', '"')));
        assertTrue(_contains(svg, "<svg xmlns='http://www.w3.org/2000/svg'"));
        assertTrue(_contains(svg, "</svg>"));
        assertTrue(_contains(svg, "SLOPWARE 000001"));
        assertTrue(_contains(uri, '"Status","value":"INSTALLED"'));
        assertTrue(_contains(uri, "Observed behavior"));
        assertTrue(_contains(uri, "UNKNOWN"));
        assertFalse(_contains(uri, "rarity"));
        assertFalse(_contains(uri, "Rarity"));
        assertFalse(_contains(uri, "score"));
        vm.expectRevert(Slopware.NoSuchRelease.selector);
        w.tokenURI(99);
    }

    // ------------------------------------------------------------ 20: gas

    function test_gas_installAndComplete() public {
        uint256 g0 = gasleft();
        uint256 id = _request(alice);
        uint256 reqGas = g0 - gasleft();
        vm.roll(w.software(id).requestedAt + 2);
        g0 = gasleft();
        w.complete(id);
        uint256 installationGas = g0 - gasleft();
        emit log_named_uint("install gas", reqGas);
        emit log_named_uint("installation gas", installationGas);
        assertLt(reqGas, 200_000);
        assertLt(installationGas, 200_000);
    }

    // ------------------------------------------------------------ batches

    function test_installMany_numbersMintsAndEmitsEach() public {
        vm.recordLogs();
        vm.prank(alice);
        (uint256 first, uint256 last) = w.installMany{value: FEE * 5}(5);
        assertEq(first, 1);
        assertEq(last, 5);
        assertEq(w.releases(), 5);
        uint256 installingEvents;
        Vm.Log[] memory logs = vm.getRecordedLogs();
        for (uint256 i = 0; i < logs.length; i++) {
            if (logs[i].topics[0] == keccak256("Installing(uint256,address,uint256,uint256)")) installingEvents++;
        }
        assertEq(installingEvents, 5);
        for (uint256 id = 1; id <= 5; id++) {
            assertEq(w.ownerOf(id), alice);
            assertEq(uint8(w.statusOf(id)), uint8(Slopware.Status.Installing));
            assertEq(w.software(id).paid, FEE);
        }
        // the next single install continues the numbering
        assertEq(_request(bob), 6);
    }

    function test_installMany_exactPriceAndBounds() public {
        vm.startPrank(alice);
        vm.expectRevert(Slopware.WrongPrice.selector);
        w.installMany{value: FEE * 3 - 1}(3);
        vm.expectRevert(Slopware.WrongPrice.selector);
        w.installMany{value: FEE * 4}(3);
        vm.expectRevert(Slopware.BadCount.selector);
        w.installMany{value: 0}(0);
        vm.expectRevert(Slopware.BadCount.selector);
        w.installMany{value: FEE * 101}(101);
        vm.stopPrank();
    }

    function test_installMany_hundredFitsInOneTransaction() public {
        vm.prank(alice);
        uint256 g = gasleft();
        w.installMany{value: FEE * 100}(100);
        uint256 used = g - gasleft();
        assertLt(used, 16_777_216, "a full batch must fit under the per-transaction gas cap");
        assertEq(w.releases(), 100);
    }

    function test_completeMany_completesDistinctAndSkipsTheRest() public {
        vm.prank(alice);
        w.installMany{value: FEE * 3}(3);
        vm.roll(block.number + 2);
        vm.prank(bob);
        uint256 four = w.install{value: FEE}(); // requested now: not ready yet
        uint256[] memory ids = new uint256[](6);
        ids[0] = 1; ids[1] = 2; ids[2] = 3; ids[3] = 3; ids[4] = four; ids[5] = 999; // a repeat, a too-soon one, a nonexistent one
        uint256 done = w.completeMany(ids);
        assertEq(done, 3, "three settled; repeat, too-soon and nonexistent passed over");
        for (uint256 id = 1; id <= 3; id++) {
            assertTrue(w.statusOf(id) == Slopware.Status.Installed || w.statusOf(id) == Slopware.Status.Rejected);
            assertEq(w.bytecodeOf(id), _expectedBytecode(id));
        }
        assertEq(uint8(w.statusOf(four)), uint8(Slopware.Status.Installing));
        assertTrue(keccak256(w.bytecodeOf(1)) != keccak256(w.bytecodeOf(2)), "same block, different bytecode");
        assertTrue(keccak256(w.bytecodeOf(2)) != keccak256(w.bytecodeOf(3)));
        // completing again changes nothing and does not revert
        assertEq(w.completeMany(ids), 0);
        // the strict path still refuses
        vm.expectRevert(Slopware.NotInstalling.selector);
        w.complete(1);
        vm.expectRevert(Slopware.TooSoon.selector);
        w.complete(four);
    }

    function _after(string memory s, string memory marker) internal pure returns (string memory) {
        bytes memory b = bytes(s);
        bytes memory m = bytes(marker);
        for (uint256 i = 0; i + m.length <= b.length; i++) {
            bool hit = true;
            for (uint256 j = 0; j < m.length; j++) if (b[i + j] != m[j]) { hit = false; break; }
            if (hit) {
                bytes memory out = new bytes(b.length - i - m.length);
                for (uint256 k = 0; k < out.length; k++) out[k] = b[i + m.length + k];
                return string(out);
            }
        }
        revert("marker not found");
    }

    function _between(string memory s, string memory start, string memory stop) internal pure returns (string memory) {
        bytes memory rest = bytes(_after(s, start));
        bytes memory e = bytes(stop);
        for (uint256 i = 0; i + e.length <= rest.length; i++) {
            bool hit = true;
            for (uint256 j = 0; j < e.length; j++) if (rest[i + j] != e[j]) { hit = false; break; }
            if (hit) {
                bytes memory out = new bytes(i);
                for (uint256 k = 0; k < i; k++) out[k] = rest[k];
                return string(out);
            }
        }
        revert("end marker not found");
    }

    function _contains(string memory hay, string memory needle) internal pure returns (bool) {
        bytes memory h = bytes(hay);
        bytes memory n = bytes(needle);
        if (n.length > h.length) return false;
        for (uint256 i = 0; i + n.length <= h.length; i++) {
            bool m = true;
            for (uint256 j = 0; j < n.length; j++) {
                if (h[i + j] != n[j]) { m = false; break; }
            }
            if (m) return true;
        }
        return false;
    }
}

contract PlainContract {}
