import warnings
warnings.filterwarnings("ignore")


from flask import Flask, request, jsonify, render_template
from web3 import Web3
import json
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Connect to Ganache
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 not connected!"

# Load contract
with open("build/contracts/MedicalVault.json") as f:
    contract_data = json.load(f)
abi = contract_data["abi"]
network_id = "1337"
contract_address = contract_data["networks"][network_id]["address"]
contract = w3.eth.contract(address=contract_address, abi=abi)
print(f"[Flask] Using contract at: {contract_address}")
account = w3.eth.accounts[0]


@app.route("/records", methods=["GET"])
def get_records():
    viewer = request.args.get("address")  # who is requesting
    count = contract.functions.recordCount().call()
    visible_records = []

    for i in range(1, count + 1):
        record = contract.functions.records(i).call()
        record_id = record[0]
        metadata = record[1]
        patient = record[2]
        is_shared = record[3]

        # Check access permission
        can_view = False
        if viewer is None:
            can_view = True  # allow all if no address (for testing)
        elif viewer.lower() == patient.lower():
            can_view = True
        else:
            can_view = contract.functions.canAccess(record_id).call({"from": viewer})

        if can_view:
            visible_records.append({
                "id": record_id,
                "metadata": metadata,
                "patient": patient,
                "isShared": is_shared
            })

    return jsonify(visible_records)



@app.route("/request-access", methods=["POST"])
def request_access():
    record_id = int(request.json["record_id"])
    requester = request.json["requester"]  # address of doctor

    tx_hash = contract.functions.requestAccess(record_id).transact({"from": requester})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return jsonify({
        "status": "access requested",
        "tx": receipt.transactionHash.hex()
    })
@app.route("/grant-access", methods=["POST"])
def grant_access():
    record_id = int(request.json["record_id"])
    patient = request.json["patient"]      # must match record owner
    provider = request.json["provider"]    # address of doctor to grant

    tx_hash = contract.functions.grantAccess(record_id, provider).transact({"from": patient})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return jsonify({
        "status": "access granted",
        "tx": receipt.transactionHash.hex()
    })
@app.route("/can-access", methods=["GET"])
def can_access():
    record_id = int(request.args.get("record_id"))
    address = request.args.get("address")

    try:
        allowed = contract.functions.canAccess(record_id).call({"from": address})
        return jsonify({"canAccess": allowed})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/upload-file-form", methods=["POST"])
def upload_file_form():
    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Upload to IPFS
    import requests
    with open(filepath, "rb") as f:
        files = {'file': f}
        res = requests.post("http://127.0.0.1:5001/api/v0/add", files=files)

    ipfs_hash = res.json()["Hash"]

    # Save IPFS hash to smart contract
    try:
        tx_hash = contract.functions.uploadRecord(ipfs_hash).transact({
            "from": account  # patient account
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        status = "Record stored on-chain"
    except Exception as e:
        status = f"Blockchain error: {e}"

    return render_template("upload.html", ipfs_hash=ipfs_hash, status=status)


@app.route("/upload-form", methods=["GET"])
def upload_form():
    return render_template("upload.html")

@app.route("/view-records", methods=["GET"])
def view_records():
    address = request.args.get("address")
    if not address:
        return render_template("records.html", records=None)

    count = contract.functions.recordCount().call()
    visible_records = []

    for i in range(1, count + 1):
        record = contract.functions.records(i).call()
        record_id = record[0]
        metadata = record[1]
        patient = record[2]
        is_shared = record[3]

        # Access control
        if address.lower() == patient.lower():
            allowed = True
        else:
            allowed = contract.functions.canAccess(record_id).call({"from": address})

        if allowed:
            visible_records.append({
                "id": record_id,
                "metadata": metadata,
                "patient": patient,
                "isShared": is_shared
            })

    return render_template("records.html", records=visible_records)

@app.route("/access", methods=["GET", "POST"])
def access_page():
    status = None
    pending = []
    patient = request.args.get("patient")

    # POST (grant or request)
    if request.method == "POST":
        action = request.form.get("action")
        record_id = int(request.form.get("record_id"))

        if action == "request":
            requester = request.form.get("requester")
            try:
                tx = contract.functions.requestAccess(record_id).transact({"from": requester})
                w3.eth.wait_for_transaction_receipt(tx)
                status = f"Access requested for record {record_id}"
            except Exception as e:
                status = f"Error requesting access: {e}"

        elif action == "grant":
            requester = request.form.get("requester")
            patient = request.form.get("patient")
            try:
                tx = contract.functions.grantAccess(record_id, requester).transact({"from": patient})
                w3.eth.wait_for_transaction_receipt(tx)
                status = f"Granted access to record {record_id} for {requester}"
            except Exception as e:
                status = f"Error while granting access: {e}"

    # GET (view pending requests)
    if patient:
        try:
            # Loop over all records, check if patient is owner, then get pending requests
            count = contract.functions.recordCount().call()
            for i in range(1, count + 1):
                rec = contract.functions.records(i).call()
                if rec[2].lower() == patient.lower():
                    try:
                        requesters = contract.functions.getAccessRequests(i).call()
                        for r in requesters:
                            pending.append({"record_id": i, "requester": r})
                    except Exception:
                        continue
        except Exception as e:
            status = f"Error loading pending requests: {e}"

    return render_template("access.html", patient=patient, requests=pending, status=status)





if __name__ == "__main__":
    app.run(debug=True)
