// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title VerificationRegistry
 * @dev A minimal smart contract for storing face verification evidence hashes
 *      on the Polygon blockchain. This contract provides tamper-evident
 *      timestamping for face verification records.
 *
 *      IMPORTANT: This contract stores ONLY cryptographic evidence hashes.
 *      It does NOT store:
 *      - Original photographs
 *      - Face embeddings/biometrics
 *      - Personal information
 *      - Social media content
 *
 *      The blockchain provides integrity and timestamping, NOT truth.
 *      False information can be hashed and stored - blockchain will
 *      faithfully preserve the hash of false information.
 */
contract VerificationRegistry {
    // Structure to store verification records
    struct VerificationRecord {
        bytes32 evidenceHash;
        uint256 timestamp;
        address submitter;
        bool exists;
    }

    // Mapping from record ID to verification record
    mapping(uint256 => VerificationRecord) public records;

    // Mapping to check if a hash already exists (for deduplication)
    mapping(bytes32 => bool) public hashExists;

    // Counter for total records
    uint256 public totalRecords;

    // Event emitted when a new verification is recorded
    event VerificationRecorded(
        uint256 indexed recordId,
        bytes32 indexed evidenceHash,
        uint256 timestamp,
        address indexed submitter
    );

    // Event emitted when a verification is accessed
    event VerificationAccessed(
        uint256 indexed recordId,
        bytes32 indexed evidenceHash,
        uint256 timestamp
    );

    /**
     * @dev Record a new verification evidence hash
     * @param evidenceHash The SHA-256 hash of the evidence JSON
     * @return recordId The ID of the created record
     */
    function recordVerification(bytes32 evidenceHash)
        external
        returns (uint256 recordId)
    {
        require(evidenceHash != bytes32(0), "Invalid evidence hash");

        totalRecords++;
        recordId = totalRecords;

        records[recordId] = VerificationRecord({
            evidenceHash: evidenceHash,
            timestamp: block.timestamp,
            submitter: msg.sender,
            exists: true
        });

        hashExists[evidenceHash] = true;

        emit VerificationRecorded(recordId, evidenceHash, block.timestamp, msg.sender);

        return recordId;
    }

    /**
     * @dev Get a verification record by ID
     * @param recordId The ID of the record to retrieve
     * @return evidenceHash The evidence hash
     * @return timestamp The timestamp when recorded
     * @return submitter The address that submitted the record
     */
    function getVerification(uint256 recordId)
        external
        view
        returns (
            bytes32 evidenceHash,
            uint256 timestamp,
            address submitter
        )
    {
        require(records[recordId].exists, "Record does not exist");

        VerificationRecord storage record = records[recordId];

        return (
            record.evidenceHash,
            record.timestamp,
            record.submitter
        );
    }

    /**
     * @dev Verify if an evidence hash exists in the registry
     * @param evidenceHash The hash to check
     * @return exists Whether the hash exists
     * @return recordId The ID of the record (0 if not found)
     */
    function verifyHash(bytes32 evidenceHash)
        external
        view
        returns (bool exists, uint256 recordId)
    {
        if (hashExists[evidenceHash]) {
            // Find the record ID by scanning (in production, consider indexed mapping)
            for (uint256 i = 1; i <= totalRecords; i++) {
                if (records[i].evidenceHash == evidenceHash) {
                    return (true, i);
                }
            }
        }
        return (false, 0);
    }

    /**
     * @dev Get the total number of verification records
     * @return The total count of records
     */
    function getTotalRecords() external view returns (uint256) {
        return totalRecords;
    }

    /**
     * @dev Check if a hash was recorded at or before a specific timestamp
     * @param evidenceHash The hash to check
     * @param maxTimestamp The maximum timestamp
     * @return recordedAt The timestamp when recorded (0 if not found or after maxTimestamp)
     */
    function getRecordTimestamp(bytes32 evidenceHash, uint256 maxTimestamp)
        external
        view
        returns (uint256 recordedAt)
    {
        for (uint256 i = 1; i <= totalRecords; i++) {
            if (records[i].evidenceHash == evidenceHash) {
                if (records[i].timestamp <= maxTimestamp) {
                    return records[i].timestamp;
                }
            }
        }
        return 0;
    }
}
