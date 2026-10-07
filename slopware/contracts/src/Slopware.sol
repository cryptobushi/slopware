// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ERC721} from "solady/tokens/ERC721.sol";
import {LibString} from "solady/utils/LibString.sol";

/*

    SLOPWARE
    software nobody wrote

    Software is written. Someone decides what it should do, and writes it,
    and it does that, more or less.

    Slopware is not written. You install it before it exists. In the next
    block, Ethereum fixes sixty-four bytes nobody chose, and those bytes
    become the whole of a program at an address of its own. Nothing reads
    them first. Nothing repairs them. Nothing tries again.

    Most of it will not run. Some of it will. Nobody knows which.

    This contract is the installer. It is the only program here anyone wrote.

*/
contract Slopware is ERC721 {
    // ---------------------------------------------------------------- what a release is

    /// Sixty-four bytes. Always.
    uint256 public constant BYTECODE_LENGTH = 64;

    /// Eleven bytes that place the sixty-four, unchanged, at an address, and stop:
    /// PUSH1 0x40 · DUP1 · PUSH1 0x0b · PUSH1 0 · CODECOPY · PUSH1 0 · RETURN
    bytes internal constant LOADER = hex"604080600b6000396000f3";

    /// Ethereum refuses to install any program whose first byte is this (EIP-3541). The refusal
    /// is Ethereum's rule, not ours; recording it directly rather than paying CREATE to fail
    /// keeps a rejection cheap, and lets a placement have every unit of gas the completer sent.
    bytes1 internal constant REFUSED_FIRST_BYTE = 0xef;

    /// The most releases one transaction may install. A hundred installs cost about eleven
    /// million gas; Ethereum caps a transaction at 2^24 (EIP-7825). Each release still gets its
    /// own bytecode: the release number is mixed into the hash, so a batch shares a deciding
    /// block and nothing else.
    uint256 public constant MAX_PER_INSTALL = 100;

    enum Status {
        None,
        Installing, // requested; the deciding block does not exist yet
        Installed, // a program is at its address; its code is the bytecode, nothing more
        Rejected, // Ethereum refused this bytecode; it is kept here instead
        Abandoned // nobody completed the installation in time; refundable
    }

    struct Software {
        address installer; // who installed it; this never changes
        uint64 requestedAt; // the block in which it was requested
        uint64 installedAt; // the block in which it completed
        Status status;
        uint96 paid;
        address program; // where it runs, if it runs
        bytes32 checksum; // keccak256 of the bytecode
    }

    // ---------------------------------------------------------------- state

    address public immutable artist;
    uint256 public price;

    /// Releases so far. Every one is numbered, whatever became of it.
    uint256 public releases;
    uint256 public installed;
    uint256 public rejected;

    mapping(uint256 => Software) internal _software;
    mapping(uint256 => bytes) internal _rejectedBytecode;
    mapping(address => uint256) public releaseOf;
    mapping(address => uint256) public refunds;
    uint256 public totalRefundable;

    event Installing(uint256 indexed release, address indexed installer, uint256 requestedAt, uint256 paid);
    event Installed(uint256 indexed release, address indexed installer, address indexed program, bytes32 checksum, bytes bytecode);
    event Rejected(uint256 indexed release, address indexed installer, bytes32 checksum, bytes bytecode, bytes32 reason);
    event Abandoned(uint256 indexed release, address indexed installer, uint256 refund);
    event PriceSet(uint256 price);

    error WrongPrice();
    error NotInstalling();
    error TooSoon();
    error NotArtist();
    error NothingToRefund();
    error NoSuchRelease();
    error BadCount();
    /// CREATE returned nothing for bytecode Ethereum does not refuse. The only cause is too little
    /// gas. Nothing is recorded; complete again with more.
    error PlacementFailed();

    constructor(address artist_, uint256 price_) {
        artist = artist_;
        price = price_;
        emit PriceSet(price_);
    }

    // ---------------------------------------------------------------- install

    /// Install slopware. You will not know what it is until the next block does.
    function install() external payable returns (uint256 release) {
        (release,) = _install(1);
    }

    /// Install several at once. Each release is numbered, minted and decided on its own;
    /// they share a transaction and a deciding block, nothing more.
    function installMany(uint256 count) external payable returns (uint256 first, uint256 last) {
        return _install(count);
    }

    function _install(uint256 count) internal returns (uint256 first, uint256 last) {
        if (count == 0 || count > MAX_PER_INSTALL) revert BadCount();
        if (msg.value != price * count) revert WrongPrice();
        uint96 paid = uint96(price);
        first = releases + 1;
        last = releases + count;
        releases = last;
        for (uint256 release = first; release <= last; release++) {
            _software[release] = Software({
                installer: msg.sender,
                requestedAt: uint64(block.number),
                installedAt: 0,
                status: Status.Installing,
                paid: paid,
                program: address(0),
                checksum: bytes32(0)
            });
            _mint(msg.sender, release); // no callback; nothing else runs during an installation
            emit Installing(release, msg.sender, block.number, paid);
        }
    }

    /// Complete an installation. Anyone may, once the deciding block is final.
    /// The bytecode is the hash of that block, mixed with the release number. Once.
    function complete(uint256 release) external {
        _complete(release, true);
    }

    /// Complete several. Releases that are not ready, or already settled, are passed over
    /// rather than failing the rest; a batch may race the collectors' own completions.
    function completeMany(uint256[] calldata releases_) external returns (uint256 done) {
        for (uint256 i = 0; i < releases_.length; i++) {
            if (_complete(releases_[i], false)) done++;
        }
    }

    function _complete(uint256 release, bool strict) internal returns (bool) {
        Software storage s = _software[release];
        if (s.status != Status.Installing) {
            if (strict) revert NotInstalling();
            return false;
        }
        uint256 decidingBlock = uint256(s.requestedAt) + 1;
        if (block.number <= decidingBlock) {
            if (strict) revert TooSoon();
            return false;
        }

        bytes32 entropy = blockhash(decidingBlock);
        if (entropy == bytes32(0)) {
            // the deciding block has left the EVM's memory; its hash is gone, and so is this release
            s.status = Status.Abandoned;
            refunds[s.installer] += s.paid;
            totalRefundable += s.paid;
            emit Abandoned(release, s.installer, s.paid);
            return true;
        }

        bytes memory bytecode = abi.encodePacked(
            keccak256(abi.encodePacked(entropy, release, uint8(0))), keccak256(abi.encodePacked(entropy, release, uint8(1)))
        );
        bytes32 checksum = keccak256(bytecode);
        s.checksum = checksum;
        s.installedAt = uint64(block.number);

        address program = _place(bytecode);
        if (program == address(0)) {
            // only refused bytecode comes back empty; _place reverts rather than return empty for anything else
            s.status = Status.Rejected;
            _rejectedBytecode[release] = bytecode;
            rejected++;
            emit Rejected(release, s.installer, checksum, bytecode, bytes32("EIP-3541"));
            return true;
        }
        if (program.code.length != BYTECODE_LENGTH || keccak256(program.code) != checksum) {
            // cannot happen with LOADER; written down rather than assumed
            s.status = Status.Rejected;
            s.program = program;
            _rejectedBytecode[release] = bytecode;
            rejected++;
            emit Rejected(release, s.installer, checksum, bytecode, bytes32("MISMATCH"));
            return true;
        }

        s.status = Status.Installed;
        s.program = program;
        releaseOf[program] = release;
        installed++;
        emit Installed(release, s.installer, program, checksum, bytecode);
        return true;
    }

    /// Place the bytecode at an address and never speak to it again. Returns the zero address
    /// only for bytecode Ethereum refuses; for anything else, a failed CREATE means the completer
    /// sent too little gas, and the whole completion reverts so nothing false is recorded.
    function _place(bytes memory bytecode) internal returns (address program) {
        if (bytecode[0] == REFUSED_FIRST_BYTE) return address(0);
        bytes memory init = abi.encodePacked(LOADER, bytecode);
        assembly ("memory-safe") {
            program := create(0, add(init, 0x20), mload(init))
        }
        if (program == address(0)) revert PlacementFailed();
    }

    // ---------------------------------------------------------------- read

    function software(uint256 release) external view returns (Software memory s) {
        s = _software[release];
        if (s.status == Status.None) revert NoSuchRelease();
    }

    /// The sixty-four bytes: read from the program itself when installed, from here when rejected.
    function bytecodeOf(uint256 release) public view returns (bytes memory) {
        Software storage s = _software[release];
        if (s.status == Status.Installed) return s.program.code;
        if (s.status == Status.Rejected) return _rejectedBytecode[release];
        return "";
    }

    function statusOf(uint256 release) external view returns (Status) {
        return _software[release].status;
    }

    // ---------------------------------------------------------------- money

    function setPrice(uint256 price_) external {
        if (msg.sender != artist) revert NotArtist();
        price = price_;
        emit PriceSet(price_);
    }

    function withdraw() external {
        uint256 amount = address(this).balance - totalRefundable;
        (bool ok,) = artist.call{value: amount}("");
        require(ok);
    }

    function claimRefund() external {
        uint256 amount = refunds[msg.sender];
        if (amount == 0) revert NothingToRefund();
        refunds[msg.sender] = 0;
        totalRefundable -= amount;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
    }

    // ---------------------------------------------------------------- the receipt

    function name() public pure override returns (string memory) {
        return "SLOPWARE";
    }

    function symbol() public pure override returns (string memory) {
        return "SLOP";
    }

    /// Facts about a release. Not the release.
    function tokenURI(uint256 release) public view override returns (string memory) {
        Software memory s = _software[release];
        if (s.status == Status.None) revert NoSuchRelease();
        string memory n = _six(release);
        string memory status = s.status == Status.Installed ? "INSTALLED" : s.status == Status.Rejected ? "REJECTED" : s.status == Status.Abandoned ? "ABANDONED" : "INSTALLING";
        bytes memory bytecode = bytecodeOf(release);
        string memory hex_ = bytecode.length > 0 ? LibString.toHexString(bytecode) : "";

        bytes memory attrs = abi.encodePacked(
            '{"trait_type":"Status","value":"', status, '"},',
            '{"trait_type":"Installer","value":"', LibString.toHexStringChecksummed(s.installer), '"},',
            '{"trait_type":"Requested at","display_type":"number","value":', LibString.toString(s.requestedAt), '}'
        );
        if (s.status == Status.Installed) {
            attrs = abi.encodePacked(
                attrs,
                ',{"trait_type":"Program","value":"', LibString.toHexStringChecksummed(s.program), '"},',
                '{"trait_type":"Installed at","display_type":"number","value":', LibString.toString(s.installedAt), '},',
                '{"trait_type":"Bytecode length","display_type":"number","value":64},',
                '{"trait_type":"Checksum","value":"', LibString.toHexString(uint256(s.checksum), 32), '"},',
                '{"trait_type":"Observed behavior","value":"UNKNOWN"}'
            );
        } else if (s.status == Status.Rejected) {
            attrs = abi.encodePacked(attrs, ',{"trait_type":"Checksum","value":"', LibString.toHexString(uint256(s.checksum), 32), '"}');
        }

        string memory desc = s.status == Status.Installed
            ? string(abi.encodePacked("Software nobody wrote. Sixty-four random bytes are the whole program at ", LibString.toHexStringChecksummed(s.program), ". What it does is unknown."))
            : s.status == Status.Rejected
                ? "Software nobody wrote, which Ethereum refused to install. The bytecode is recorded here; no program exists."
                : s.status == Status.Abandoned ? "An installation nobody completed in time. No bytecode was produced." : "An installation awaiting its deciding block.";

        return string(
            abi.encodePacked(
                "data:application/json;utf8,",
                '{"name":"SLOPWARE ', n, '","description":"', desc, '",',
                '"image":"data:image/svg+xml;utf8,', _svg(n, status, s, hex_), '",',
                '"attributes":[', attrs, "]}"
            )
        );
    }

    function _svg(string memory n, string memory status, Software memory s, string memory hex_) internal pure returns (bytes memory) {
        bytes memory lines = abi.encodePacked(
            "<text x='40' y='70' font-size='22' letter-spacing='6'>SLOPWARE ", n, "</text>",
            "<text x='40' y='120' font-size='14' letter-spacing='4'>", status, "</text>"
        );
        if (s.status == Status.Installed) {
            lines = abi.encodePacked(lines, "<text x='40' y='170' font-size='11'>", LibString.toHexStringChecksummed(s.program), "</text>");
        }
        if (bytes(hex_).length > 0) {
            bytes memory g = bytes(hex_);
            for (uint256 i = 0; i < 4; i++) {
                bytes memory row = new bytes(32);
                for (uint256 j = 0; j < 32; j++) row[j] = g[2 + i * 32 + j];
                lines = abi.encodePacked(lines, "<text x='40' y='", LibString.toString(220 + i * 20), "' font-size='11'>", row, "</text>");
            }
        }
        lines = abi.encodePacked(lines, "<text x='40' y='330' font-size='11'>installed by ", LibString.toHexStringChecksummed(s.installer), "</text>");
        return abi.encodePacked(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400' font-family='Courier New,monospace' fill='#000'>",
            "<rect width='400' height='400' fill='#fff'/>",
            lines,
            "</svg>"
        );
    }

    function _six(uint256 v) internal pure returns (string memory) {
        bytes memory b = bytes(LibString.toString(v));
        if (b.length >= 6) return string(b);
        bytes memory out = new bytes(6);
        uint256 pad = 6 - b.length;
        for (uint256 i = 0; i < pad; i++) out[i] = "0";
        for (uint256 i = 0; i < b.length; i++) out[pad + i] = b[i];
        return string(out);
    }
}
