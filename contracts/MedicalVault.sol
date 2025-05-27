// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicalVault {
    struct Record {
        uint id;
        string metadataHash;
        address patient;
        bool isShared;
    }

    struct Access {
        address provider;
        bool approved;
    }

    uint public recordCount;
    mapping(uint => Record) public records;
    mapping(uint => Access[]) public accessRequests;

    event RecordUploaded(uint id, address patient, string metadataHash);
    event AccessRequested(uint recordId, address provider);
    event AccessGranted(uint recordId, address provider);

    function uploadRecord(string memory _metadataHash) public {
        recordCount++;
        records[recordCount] = Record(recordCount, _metadataHash, msg.sender, false);
        emit RecordUploaded(recordCount, msg.sender, _metadataHash);
    }

    function requestAccess(uint _recordId) public {
        accessRequests[_recordId].push(Access(msg.sender, false));
        emit AccessRequested(_recordId, msg.sender);
    }

    function grantAccess(uint _recordId, address _provider) public {
        require(records[_recordId].patient == msg.sender, "Only patient can grant");
        for (uint i = 0; i < accessRequests[_recordId].length; i++) {
            if (accessRequests[_recordId][i].provider == _provider) {
                accessRequests[_recordId][i].approved = true;
                records[_recordId].isShared = true;
                emit AccessGranted(_recordId, _provider);
                break;
            }
        }
    }

    function canAccess(uint _recordId) public view returns (bool) {
        if (records[_recordId].patient == msg.sender) return true;
        for (uint i = 0; i < accessRequests[_recordId].length; i++) {
            if (
                accessRequests[_recordId][i].provider == msg.sender &&
                accessRequests[_recordId][i].approved
            ) {
                return true;
            }
        }
        return false;
    }

    // ✅ New function to get pending access requests
    function getAccessRequests(uint _recordId) public view returns (address[] memory) {
        uint total = 0;
        for (uint i = 0; i < accessRequests[_recordId].length; i++) {
            if (!accessRequests[_recordId][i].approved) {
                total++;
            }
        }

        address[] memory pending = new address[](total);
        uint index = 0;
        for (uint i = 0; i < accessRequests[_recordId].length; i++) {
            if (!accessRequests[_recordId][i].approved) {
                pending[index] = accessRequests[_recordId][i].provider;
                index++;
            }
        }

        return pending;
    }
}
