from beaker import sandbox

from src.utils.accounts import *
from pyteal import *
from beaker import *
from typing import Final
from algosdk.future import transaction

# Create a class, subclassing Application from beaker
from src.utils.client import get_algod_client


class BorrowMyNFT(Application):
    nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A handle to retrieve the correct NFT",
    )
    borrower_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The address of the borrower",
    )
    lender_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Current highest bidder",
    )
    highest_bid: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Highest bid",
    )
    loan_threshold: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Auction starting amount",
    )
    auction_period: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        # 1 day = 86400 seconds, 1 block = 5 seconds, 1 day = 17280 blocks
        default=Int(17280),
        descr="Number of blocks from the offer creation",
    )
    payback_deadline: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        # 1 day = 86400 seconds, 1 block = 5 seconds, 1 day = 17280 blocks
        default=Int(17280),
        descr="Number of blocks from the bid acceptance",
    )
    last_interest_update_block: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="starting block to compute the interest. It stores the block corresponding to the last successful "
              "invocation of PayBack",
    )
    debt_left: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block",
    )

    # Contract address minimum balance
    MIN_BAL = Int(100000)

    # Algorand minimum txn fee
    FEE = Int(1000)

    @create
    def create(self):
        """Deploys the contract and intialize app states"""
        return self.initialize_application_state()

    @opt_in
    def opt_in(self):
        # No local state to set, so approve
        return Approve()

    @close_out
    def close_out(self):
        return Approve()

    @delete(authorize=Authorize.only(Global.creator_address()))
    def delete(self):
        return Approve()

    # Add an external method with ABI method signature `hello(string)string`
    @external
    def health(self, output: abi.String):
        # Set output to the result of `Hello, `+name
        return output.set(
            Bytes(
                f"Contract {Global.current_application_id()} is up and running"
            )
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def PayMe(self, receiver: abi.Account):
        return InnerTxnBuilder.Execute({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: Minus(Balance(Global.current_application_address()),
                                   Add(MinBalance(Global.current_application_address()), Global.min_txn_fee())),
            TxnField.receiver: receiver.address(),
            TxnField.fee: Global.min_txn_fee()
        })

    # @external
    # def Offer(nft: abi.String, loan_threshold: abi.Uint64, auction_period: abi.Uint64, payback_deadline: abi.Uint64):
    #     # borrower_address=tx.sender; nft=?????
    #     pass

    # @external
    # def Bid (n_algos: abi.Uint64):
    # lender_address=tx.sender; n_algos=?????
    # pass

    # @external
    # def AcceptBid ():
    # pass

    # @external
    # def Timeout ():
    # pass

    # @external
    # def CancelOffer ():
    # pass

    # @external
    # def PayBack (m_algos:abi.Uint64):
    # current_block = ????Global.block+1 ; m_algos=?????
    # pass

    # @external
    # def LoanExpires ():
    # pass


def demo():
    # Create an Application client
    all_sandbox_accounts = sandbox.get_accounts()
    contract_owner = all_sandbox_accounts.pop()
    borrower = all_sandbox_accounts.pop()
    lender = all_sandbox_accounts.pop()

    acc = sandbox.get_accounts().pop()
    app_client = client.ApplicationClient(
        # Get sandbox algod client
        client=sandbox.get_algod_client(),
        # Instantiate app with the program version (default is MAX_TEAL_VERSION)
        app=BorrowMyNFT(version=6),
        # Get acct from sandbox and pass the signer
        signer=acc.signer  # pop().signer,
    )

    # Deploy the app on-chain
    app_id, app_addr, txid = app_client.create()
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id} 
        Address: {app_addr} 
    """
    )
    print(app_client.client.account_info(acc.address).get('amount'))
    app_client.fund(5 * consts.algo)
    print(app_client.client.account_info(acc.address).get('amount'))
    result = app_client.call(BorrowMyNFT.PayMe, receiver=acc.address)
    print(result.return_value, result.decode_error)
    print((app_client.client.account_info(acc.address)).get('amount'))
    print(acc.address)
    # params = app_client.get_suggested_params()
    # receiver=app_client.get_application_account_info().address
    # note = "Hello World".encode()
    # amount = 1000000
    # unsigned_txn = transaction.PaymentTxn(app_client.get_sender(), params, receiver, amount, None, note)
    # signed_txn=unsigned_txn.sign(acc.private_key)
    # txid = app_client.send_transaction(signed_txn)
    # print("Successfully sent transaction with txID: {}".format(txid))
    # try:
    #    confirmed_txn = transaction.wait_for_confirmation(app_client, txid, 4)  

    # except Exception as err:
    #    print(err)
    #    return


if __name__ == "__main__":
    demo()
