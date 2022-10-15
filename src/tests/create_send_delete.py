import json

from algosdk.future import transaction
from algosdk.atomic_transaction_composer import TransactionWithSigner, AtomicTransactionComposer
from beaker import sandbox, consts
from beaker.client import ApplicationClient, LogicException

from src.contract import BorrowMyNFT
from src.nft import create_default_nft
from src.tests.nft_test import nft_metadata_github_url

client = sandbox.get_algod_client()
accounts = sandbox.get_accounts()

contract_owner_account = accounts.pop()
borrower_account = accounts.pop()
lender_account = accounts.pop()

# Create instance of the BorrowMyNFT contract
app = BorrowMyNFT()

# Create an Application client for event creator containing both an algod client and the app
app_client = ApplicationClient(
    client,
    app,
    signer=contract_owner_account.signer
)


def create_send_delete():
    print("### CREATE, SET OFFER AND DELETE CONTRACT ### \n")
    app_id, app_addr, txid = app_client.create()
    print(f"Deployed app in txid {txid}")

    # Fund the contract for minimum balance
    app_client.fund(1 * consts.algo)
    print(f"Contract Balance: {client.account_info(app_addr).get('amount')} microAlgos \n")

    # Opt in not mandatory, contract_owner included
    # app_client.opt_in()
    health = app_client.call(app.health)
    print(f"Health: {health.return_value} \n")

    # Guest 1
    print("### BORROWER SCENARIO ###\n")
    app_client_borrower = app_client.prepare(
        signer=borrower_account.signer
    )

    print("Creating NFT")
    asset_id = create_default_nft(sandbox.get_algod_client(), borrower_account.private_key, borrower_account.address, "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("Created NFT with asset ID: {}".format(asset_id))

    #  Providing nft info and payment to allow contract opt in
    print("Send nft info and payment to allow contract opt in")
    sp = client.suggested_params()
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            borrower_account.address,
            sp,
            app_addr,
            100*consts.milli_algo
        ),
        signer=borrower_account.signer,
    )
    sp.flat_fee = True
    sp.fee = 2000
    app_client_borrower.call(
        app.provide_access_to_nft,
        suggested_params=sp,
        nft=asset_id,
        payment=payment_txn,
    )
    print("Provided access to NFT\n")

    # Read state from owner account
    print("Reading state from owner account")
    state = app_client.call(app.read_state)
    print(f"State: {state.return_value} \n")

    # Set offer
    print("Setting offer")
    sp = client.suggested_params()
    asset_xfer_txn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            sender=borrower_account.address,
            receiver=app_addr,
            sp=sp,
            index=asset_id,
            amt=1,
        ),
        signer=borrower_account.signer,
    )
    app_client_borrower.call(
        app.set_offer,
        suggested_params=sp,
        asset_xfer=asset_xfer_txn,
        auction_base=1000,
        auction_period=100,
        payback_deadline=100,
    )
    print("Offer set\n")

    # Read state from owner account
    print("Getting whole state from owner account")
    state = app_client.get_application_state()
    print(f"State: {json.dumps(state, indent=4)} \n")

    #  Cancelling offert
    print("Cancelling offer")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 3000
    # need passing asset id as foreign, contract search referenced id (saved in state) in that array
    app_client_borrower.call(
        app.cancel_offer,
        suggested_params=sp,
        foreign_assets=[asset_id],
    )

    # Read state from owner account
    print("Getting whole state from owner account")
    state = app_client.get_application_state()
    print(f"State: {json.dumps(state, indent=4)} \n")

    # Delete contract
    print("Deleting contract")
    try:
        # need double fee from owner to get back money
        sp = client.suggested_params()
        sp.flat_fee = True
        sp.fee = 2000
        app_client.delete(
            suggested_params=sp,
        )
        print("Contract deleted")
    except LogicException as e:
        print(f"Logic Exception: {e}")


    print("### END ###\n")


if __name__ == "__main__":
    create_send_delete()
