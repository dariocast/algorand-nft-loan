import json
import logging

from algosdk.future import transaction
from algosdk.atomic_transaction_composer import TransactionWithSigner, AtomicTransactionComposer
from beaker import sandbox, consts
from beaker.client import ApplicationClient, LogicException

from src.contract import BorrowMyNFT
from src.nft import create_default_nft
from src.tests.nft_test import nft_metadata_github_url
from src.utils import utils

# CONSTANTS
AUCTION_DURATION=2
LOAN_DURATION=1

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


def scenarios():
    print("### NFT LOAN MANAGER SCENARIOS ###\n")

    print(">>> SCENARIO 0: App setup <<<\n")

    # Read accounts balances
    print("- Getting accounts balances")
    print(f"\t- Borrower balance: {client.account_info(borrower_account.address)['amount']}")
    print(f"\t- Lender balance: {client.account_info(lender_account.address)['amount']}")
    print(f"\t- Contract owner balance: {client.account_info(contract_owner_account.address)['amount']}")

    # Create App
    print("- Contract owner creating app")
    app_id, app_addr, txid = app_client.create()
    print(f"- App created in txid: {txid} with:\n\tapp_id: {app_id}\n\tapp_addr: {app_addr}\n")

    # Fund the contract for minimum balance
    app_client.fund(1 * consts.algo)
    print(f"- Contract Balance: {client.account_info(app_addr).get('amount')} microAlgos \n")

    print(">>> SCENARIO 1: Loan complete flow ###\n")
    app_client_borrower = app_client.prepare(
        signer=borrower_account.signer
    )
    app_client_lender = app_client.prepare(
        signer=lender_account.signer
    )

    print("- Borrower minting NFT")
    asset_id = create_default_nft(sandbox.get_algod_client(), borrower_account.private_key, borrower_account.address,
                                  "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("- NFT minted with asset ID: {}".format(asset_id))

    #  Providing nft info and payment to allow contract opt in
    print("- Send NFT info and MIN_BALANCE payment to contract")
    sp = client.suggested_params()
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            sender=borrower_account.address,
            sp=sp,
            receiver=app_addr,
            amt=100 * consts.milli_algo,
            note=b'To allow contrat opt in'
        ),
        signer=borrower_account.signer,
    )
    # Double fee to cover inner transaction fee
    sp.flat_fee = True
    sp.fee = 2000
    app_client_borrower.call(
        app.provide_access_to_nft,
        suggested_params=sp,
        nft=asset_id,
        payment=payment_txn,
    )
    print("- Provided access to NFT")

    # Read state from owner account
    print("- Getting whole state from owner account")
    state = app_client_borrower.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")

    # Set offer
    print("- Borrower setting offer")
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
    current_round = client.status().get('last-round')
    print(f"- Current round: {current_round}")
    ending_auction_round = current_round + AUCTION_DURATION  # about ten minutes
    app_client_borrower.call(
        app.set_offer,
        suggested_params=sp,
        asset_xfer=asset_xfer_txn,
        auction_base=100,  # milliAlgos, 0.1 Algo
        auction_period=ending_auction_round,  # n. of blocks
        payback_deadline=LOAN_DURATION,  # n. of blocks after accepting the offer
    )
    print("- Offer set")

    # Read state from borrower account
    print("- Getting whole state from borrower account")
    state = app_client_borrower.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")

    # Lender place a bid
    print("- Lender placing a bid")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            sender=lender_account.address,
            sp=sp,
            receiver=app_addr,
            amt=200 * consts.milli_algo,
            note=b'Lender bidding 200 milliAlgos'
        ),
        signer=lender_account.signer,
    )
    app_client_lender.call(
        app.place_bid,
        suggested_params=sp,
        payment=payment_txn,
    )
    print("- Bid placed")

    # Read state from borrower account
    print("- Getting whole state from lender account")
    state = app_client_lender.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")

    utils.wait_for_round(client, ending_auction_round)

    # Borrower accept the offer
    print("- Borrower accepting the offer")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    app_client_borrower.call(
        app.accept_bid,
        suggested_params=sp,
    )
    print("- Offer accepted")

    # Read state from borrower account
    print("- Getting whole state from borrower account")
    state = app_client_borrower.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")

    # NFT borrower paybacks the loan
    print("- NFT borrower paybacks  part of the loan")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 3000
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            sender=borrower_account.address,
            sp=sp,
            receiver=app_addr,
            amt=100 * consts.milli_algo,
            note=b'To payback the money lender',
        ),
        signer=borrower_account.signer,
    )
    app_client_borrower.call(
        app.pay_back,
        suggested_params=sp,
        payment=payment_txn,
        foreign_assets=[asset_id],
        accounts=[lender_account.address],
    )

    # Read state from borrower account
    print("- Getting whole state from borrower account")
    state = app_client_borrower.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")

    # Wait for loan period to end
    current_round = client.status().get('last-round')
    print(f"- Current round: {current_round}")
    utils.wait_for_round(client, current_round + LOAN_DURATION + 1) # +1 to be sure

    # Lender claim the NFT after loan period expired
    print("- Lender claiming the NFT")
    # Lender must optin to asset
    print("\t- Lender opting in to NFT to receive it")
    utils.opt_in_to_asset(client, lender_account, asset_id)
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    app_client_lender.call(
        app.loan_expired,
        suggested_params=sp,
        foreign_assets=[asset_id],
    )
    print("- NFT claimed")

    # Read accounts balances
    print("- Getting accounts balances")
    print(f"\t- Borrower balance: {client.account_info(borrower_account.address)['amount']}")
    print(f"\t- Lender balance: {client.account_info(lender_account.address)['amount']}")
    print(f"\t- Contract owner balance: {client.account_info(contract_owner_account.address)['amount']}")

    # Delete contract
    print("- Deleting contract")
    try:
        # need double fee from owner to get back money
        sp = client.suggested_params()
        sp.flat_fee = True
        sp.fee = 2000
        app_client.delete(
            suggested_params=sp,
        )
        print("- Contract deleted")
    except LogicException as e:
        print(f"Logic Exception: {e}")

    #  Cancelling offert
    # print("Cancelling offer")
    # sp = client.suggested_params()
    # sp.flat_fee = True
    # sp.fee = 3000
    # # need passing asset id as foreign, contract search referenced id (saved in state) in that array
    # app_client_borrower.call(
    #     app.cancel_offer,
    #     suggested_params=sp,
    #     foreign_assets=[asset_id],
    # )
    #
    # # Read state from owner account
    # print("Getting whole state from owner account")
    # state = app_client.get_application_state()
    # print(f"State: {json.dumps(state, indent=4)} \n")
    #
    print("### END ###\n")


if __name__ == "__main__":
    scenarios()
