pragma solidity ^0.8.24;

contract UrbanTwinRegistry {
    address public immutable owner;

    struct Anchor {
        bytes32 dataHash;
        uint256 blockIndex;
        uint256 anchoredAt;
        bool exists;
    }

    mapping(bytes32 => Anchor) private anchors;

    event RecordAnchored(
        bytes32 indexed assetKey,
        uint256 indexed recordId,
        bytes32 dataHash,
        uint256 blockIndex,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function makeKey(string calldata assetId, uint256 recordId)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(assetId, recordId));
    }

    function anchorRecord(
        string calldata assetId,
        uint256 recordId,
        bytes32 dataHash,
        uint256 blockIndex
    ) external onlyOwner {
        require(bytes(assetId).length > 0, "empty asset id");
        require(dataHash != bytes32(0), "empty data hash");

        bytes32 key = makeKey(assetId, recordId);
        require(!anchors[key].exists, "record already anchored");

        anchors[key] = Anchor({
            dataHash: dataHash,
            blockIndex: blockIndex,
            anchoredAt: block.timestamp,
            exists: true
        });

        emit RecordAnchored(
            key,
            recordId,
            dataHash,
            blockIndex,
            block.timestamp
        );
    }

    function verifyRecord(
        string calldata assetId,
        uint256 recordId,
        bytes32 expectedHash
    ) external view returns (bool) {
        Anchor memory anchor = anchors[makeKey(assetId, recordId)];
        return anchor.exists && anchor.dataHash == expectedHash;
    }

    function getAnchor(string calldata assetId, uint256 recordId)
        external
        view
        returns (
            bytes32 dataHash,
            uint256 blockIndex,
            uint256 anchoredAt,
            bool exists
        )
    {
        Anchor memory anchor = anchors[makeKey(assetId, recordId)];
        return (
            anchor.dataHash,
            anchor.blockIndex,
            anchor.anchoredAt,
            anchor.exists
        );
    }
}
