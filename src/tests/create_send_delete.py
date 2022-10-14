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
app_client = ApplicationClient(client, app, signer=contract_owner_account.signer)


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
    app_client_borrower = app_client.prepare(signer=borrower_account.signer)

    print("Creating NFT")
    asset_id = create_default_nft(sandbox.get_algod_client(), borrower_account.private_key, borrower_account.address, "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("Created NFT with asset ID: {}".format(asset_id))
    try:
        print("Preparing 3 transactions")
        atc = AtomicTransactionComposer()
        sp = client.suggested_params()
        sp.flat_fee = True
        sp.fee = 2000
        app_client_borrower.add_method_call(
            atc=atc,
            method=app.provide_access_to_nft,
            suggested_params=sp,
            nft_id=asset_id
        )
        sp = client.suggested_params()
        asset_xfer_txn = TransactionWithSigner(
                txn=transaction.AssetTransferTxn(
                    sender=borrower_account.address,
                    receiver=app_addr,
                    amt=1,
                    index=asset_id,
                    sp=sp
                ),
                signer=borrower_account.signer
            )
        # atc.add_transaction(
        #     txn_and_signer=asset_xfer_txn
        # )
        app_client_borrower.add_method_call(
            atc=atc,
            method=app.set_offer,
            suggested_params=sp,
            asset_xfer=asset_xfer_txn,
            loan_threshold=2,
            auction_period=sp.first+17280,
            payback_deadline=sp.first+17280*2
        )

        print("Executing 3 transactions")
        results = atc.execute(client, wait_rounds=2)

        # wait for confirmation
        print("TXID: ", results.tx_ids[0])
        print("Result confirmed in round: {}".format(results.confirmed_round))
    except LogicException as e:
        print(e)

    try:
        # app_client.close_out()
        app_client.delete()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    create_send_delete()
