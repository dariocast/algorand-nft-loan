from ast import Global
import json
from time import sleep

from algosdk.future import transaction
from algosdk.atomic_transaction_composer import TransactionWithSigner
from beaker import consts, sandbox
from beaker.client import ApplicationClient, LogicException

from src.contract import BorrowMyNFT
from src.utils import nft_metadata_github_url
from src import utils

# CONSTANTS
# NB. If you use sandbox use lower DURATIONs values (e.g. 2) else 5-10 is good for testnet
AUCTION_DURATION = 2
LOAN_DURATION = 2

# Flag to use sandbox or not
SANDBOX = True

# Use testnet or sandbox
client = sandbox.get_algod_client() if SANDBOX else utils.get_algod_client()
accounts = sandbox.get_accounts() if SANDBOX else utils.get_testnet_account()

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


def demo():
    print("### NFT LOAN MANAGER SCENARIOS ###\n")

    print(">>> SCENARIO 0: App setup <<<\n")

    # Read accounts balances
    print("Getting accounts balances")
    print(f"\tBorrower balance: {client.account_info(borrower_account.address)['amount']}")
    print(f"\tLender balance: {client.account_info(lender_account.address)['amount']}")
    print(f"\tContract owner balance: {client.account_info(contract_owner_account.address)['amount']}")

    # Create App
    print("Contract owner creating app")
    app_id, app_addr, txid = app_client.create()
    print(f"App created in txid: {txid} with:\n\tapp_id: {app_id}\n\tapp_addr: {app_addr}\n")

    # Fund the contract for minimum balance
    app_client.fund(1 * consts.algo)
    print(f"Contract Balance: {client.account_info(app_addr).get('amount')} microAlgos \n")

    print(">>> SCENARIO 1: Loan complete flow <<<\n")
    app_client_borrower = app_client.prepare(
        signer=borrower_account.signer
    )
    app_client_lender = app_client.prepare(
        signer=lender_account.signer
    )

    print("Borrower minting NFT")
    asset_id = utils.create_default_nft(client, borrower_account.private_key, borrower_account.address,
                                        "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("NFT minted with asset ID: {}".format(asset_id))
    #  Providing nft info and payment to allow contract opt in
    allow_contract_to_opt_in(app_addr, app_client_borrower, asset_id)

    # Read state from owner account
    read_global_state(app_client)

    # Set offer
    ending_auction_round = set_new_offer(
        app_addr=app_addr,
        app_client_to_use=app_client_borrower,
        asset_id=asset_id,
        auction_base=100,
        auction_duration=AUCTION_DURATION,
    )

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Lender place a bid
    place_bid(app_addr, app_client_lender, bid_amount=200)

    # Read state from borrower account
    read_global_state(app_client_lender, "lender")

    utils.wait_for_round(client, ending_auction_round)

    # Borrower accept the offer
    accept_offer(app_client_borrower)

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # NFT borrower paybacks the loan
    amount_to_payback = 200
    pay_back(app_client_borrower, app_addr, amount_to_payback, asset_id)

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Asset holdings
    print("Borrower asset holdings")
    utils.print_asset_holding(client, borrower_account.address)
    print("Lender asset holdings")
    utils.print_asset_holding(client, lender_account.address)
    print("Contract asset holdings")
    utils.print_asset_holding(client, app_addr)

    print(">>> SCENARIO 2: Lender calls timeout as borrower is not accepting any offer <<<\n")

    #  Providing nft info and payment to allow contract opt in
    allow_contract_to_opt_in(app_addr, app_client_borrower, asset_id)

    # Read state from owner account
    read_global_state(app_client)

    # Set offer
    ending_auction_round = set_new_offer(
        app_addr=app_addr,
        app_client_to_use=app_client_borrower,
        asset_id=asset_id,
        auction_base=100,
        auction_duration=AUCTION_DURATION,
    )

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Lender place a higher bid
    place_bid(app_addr, app_client_lender, bid_amount=2)

    # Read state from lender account
    read_global_state(app_client_lender, "lender")
    while (client.status().get('last-round') < ending_auction_round+2):
        app_client.fund(100 * consts.milli_algo)
        print("Waiting for round ", ending_auction_round+2)
        sleep(30)
        print("Current round ", client.status().get('last-round'))

    # Read state from lender account
    read_global_state(app_client_lender, "lender")

    # Lender invokes timeout
    timeout(app_client_lender, asset_id, borrower_account.address)

    # Read state from lender account
    read_global_state(app_client_lender, "lender")

    # Asset holdings
    print("Borrower asset holdings")
    utils.print_asset_holding(client, borrower_account.address)
    print("Lender asset holdings")
    utils.print_asset_holding(client, lender_account.address)
    print("Contract asset holdings")
    utils.print_asset_holding(client, app_addr)

    print(">>> SCENARIO 3: Borrower cancel offer before auction finishes <<<\n")
    #  Providing nft info and payment to allow contract opt in
    allow_contract_to_opt_in(app_addr, app_client_borrower, asset_id)

    # Read state from owner account
    read_global_state(app_client)

    # Set offer
    ending_auction_round = set_new_offer(
        app_addr=app_addr,
        app_client_to_use=app_client_borrower,
        asset_id=asset_id,
        auction_base=100,
        auction_duration=AUCTION_DURATION,
    )

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Cancel offer
    cancel_offer(app_client_borrower, asset_id)

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Asset holdings
    print("Borrower asset holdings")
    utils.print_asset_holding(client, borrower_account.address)
    print("Lender asset holdings")
    utils.print_asset_holding(client, lender_account.address)
    print("Contract asset holdings")
    utils.print_asset_holding(client, app_addr)

    print(">>> SCENARIO 4: Lender claim NFT after incomplete payback <<<\n")

    #  Providing nft info and payment to allow contract opt in
    allow_contract_to_opt_in(app_addr, app_client_borrower, asset_id)

    # Read state from owner account
    read_global_state(app_client)

    # Set offer
    ending_auction_round = set_new_offer(
        app_addr=app_addr,
        app_client_to_use=app_client_borrower,
        asset_id=asset_id,
        auction_base=100,
        auction_duration=AUCTION_DURATION,
    )

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Lender place a bid
    place_bid(app_addr, app_client_lender, bid_amount=200)

    # Read state from borrower account
    read_global_state(app_client_lender, "lender")

    utils.wait_for_round(client, ending_auction_round)

    # Borrower accept the offer
    accept_offer(app_client_borrower)

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # NFT borrower paybacks the loan
    amount_to_payback = 100
    pay_back(app_client_borrower, app_addr, amount_to_payback, asset_id)

    # Read state from borrower account
    read_global_state(app_client_borrower, "borrower")

    # Wait for loan period to end
    current_round = client.status().get('last-round')
    print(f"Current round: {current_round}")
    utils.wait_for_round(client, current_round + LOAN_DURATION + 1)  # +1 to be sure

    # Lender claim the NFT after loan period expired
    claim_nft_after_loan_expiration(app_client_lender, asset_id)

    # Asset holdings
    print("Borrower asset holdings")
    utils.print_asset_holding(client, borrower_account.address)
    print("Lender asset holdings")
    utils.print_asset_holding(client, lender_account.address)
    print("Contract asset holdings")
    utils.print_asset_holding(client, app_addr)

    print(">>> SCENARIO 5: Owner call pay me to recollect every Algo on the contract <<<\n")

    # Read contract balance
    print(f"Contract Balance before pay_me: {client.account_info(app_addr).get('amount')} microAlgos \n")

    # Owner claims algos
    pay_me(app_client, app_addr)

    # Read again contract balance
    print(f"Contract Balance after pay_me: {client.account_info(app_addr).get('amount')} microAlgos \n")

    # Read accounts balances
    print("Getting accounts balances")
    print(f"\tBorrower balance: {client.account_info(borrower_account.address)['amount']}")
    print(f"\tLender balance: {client.account_info(lender_account.address)['amount']}")
    print(f"\tContract owner balance: {client.account_info(contract_owner_account.address)['amount']}")

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


def pay_me(app_client_to_use, app_addr):
    print("> Paying contract creator")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    # need passing asset id as foreign, contract search referenced id (saved in state) in that array
    app_client_to_use.call(
        app.pay_me,
        suggested_params=sp,
    )


def cancel_offer(app_client_to_use, asset_id):
    print("> Cancelling offer")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 3000
    # need passing asset id as foreign, contract search referenced id (saved in state) in that array
    app_client_to_use.call(
        app.cancel_offer,
        suggested_params=sp,
        foreign_assets=[asset_id],
    )

def timeout(app_client_to_use, asset_id, foreign_addr):
    print("> Cancelling offer (timeout)")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 3000
    # need passing asset id as foreign, contract search referenced id (saved in state) in that array
    app_client_to_use.call(
        app.timeout,
        suggested_params=sp,
        foreign_assets=[asset_id],
        accounts=[foreign_addr]
    )


def claim_nft_after_loan_expiration(app_client_to_use, asset_id):
    print("> Lender claiming the NFT")
    # Lender must optin to asset
    print("\tLender opting in to NFT to receive it")
    utils.opt_in_to_asset(client, lender_account, asset_id)
    print("\tLender opted in to NFT")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    app_client_to_use.call(
        app.loan_expired,
        suggested_params=sp,
        foreign_assets=[asset_id],
    )
    print("Lender now holds:")
    utils.print_asset_holding(client, lender_account.address, asset_id)
    print("NFT claimed")


def pay_back(app_client_to_use, app_addr, amount_to_payback, asset_id):
    print(f"> NFT borrower paybacks {amount_to_payback} of the loan")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 4000
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            sender=borrower_account.address,
            sp=sp,
            receiver=app_addr,
            amt=amount_to_payback * consts.milli_algo,
            note=b'To payback the money lender',
        ),
        signer=borrower_account.signer,
    )
    app_client_to_use.call(
        app.pay_back,
        suggested_params=sp,
        payment=payment_txn,
        foreign_assets=[asset_id],
        accounts=[lender_account.address],
    )


def accept_offer(app_client_to_use):
    print("> Borrower accepting the offer")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    app_client_to_use.call(
        app.accept_bid,
        suggested_params=sp,
    )
    print("Offer accepted")


def place_bid(app_addr, app_client_to_use, bid_amount):
    print("> Lender placing a bid")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            sender=lender_account.address,
            sp=sp,
            receiver=app_addr,
            amt=bid_amount * consts.milli_algo,
            note=b'Lender bidding 200 milliAlgos'
        ),
        signer=lender_account.signer,
    )
    app_client_to_use.call(
        app.place_bid,
        suggested_params=sp,
        payment=payment_txn,
    )
    print("Bid placed")


def set_new_offer(app_addr, app_client_to_use, asset_id, auction_base, auction_duration):
    print("> Borrower setting offer")
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
    print(f"Current round: {current_round}")
    ending_auction_round = current_round + auction_duration  # about ten minutes
    app_client_to_use.call(
        app.set_offer,
        suggested_params=sp,
        asset_xfer=asset_xfer_txn,
        auction_base=auction_base,  # milliAlgos, 0.1 Algo
        auction_period=auction_duration,  # n. of blocks
        payback_deadline=LOAN_DURATION,  # n. of blocks after accepting the offer
        foreign_assets=[asset_id],
    )
    print("Offer set")
    return ending_auction_round


def read_global_state(app_client_to_use, role="owner"):
    print(f"> Getting whole state from {role} account")
    state = app_client_to_use.get_application_state()
    print(f"State: {json.dumps(state, indent=4)}")


def allow_contract_to_opt_in(app_addr, app_client_to_use, asset_id):
    print("> Send NFT info and MIN_BALANCE payment to contract")
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
    app_client_to_use.call(
        app.provide_access_to_nft,
        suggested_params=sp,
        nft=asset_id,
        payment=payment_txn,
    )
    print("Provided access to NFT")


if __name__ == "__main__":
    demo()