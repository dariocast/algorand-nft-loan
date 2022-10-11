from src.utils.accounts import *
from pyteal import *
from beaker import *
from typing import Final
from algosdk.future import transaction

# Create a class, subclassing Application from beaker
class HelloBeaker(Application):

    nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="A handle to retrieve the correct NFT",
    )
    borrower_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The address of the borrower",
    )
    lender_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Current bidder",
    )
    n_algos: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Highest bid",
    )
    loan_threshold: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Auction staring amount",
    )
    auction_period: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Number of blocks from the offer creation",
    )
    payback_deadline: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Number of blocks from the bid acceptance",
    )
    last_interest_update_block: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="starting block to compute the interest. It stores the block corresponding to the last successful invocation of PayBack",
    )
    debt_left: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block",
    )

    @create
    def create(self):
        return self.initialize_application_state()

    @external(authorize=Authorize.only(Global.creator_address()))
    def PayMe(self, receiver: abi.Account):
        return InnerTxnBuilder.Execute({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: Minus(Balance(Global.current_application_address()), Add(MinBalance(Global.current_application_address()), Global.min_txn_fee())),
            TxnField.receiver: receiver.address(),
            TxnField.fee: Global.min_txn_fee()
        })

    #@external    
    #def Offer (nft: abi.String, loan_threshold: abi.Uint64, auction_period:abi.Uint64, payback_deadline:abi.Uint64):
        # borrower_address=tx.sender; nft=?????
        #pass

    #@external    
    #def Bid (n_algos: abi.Uint64):
       # lender_address=tx.sender; n_algos=?????
       #pass 

    #@external    
    #def AcceptBid ():
       #pass

    #@external    
    #def Timeout ():
       #pass    

    #@external    
    #def CancelOffer ():
       #pass 

    #@external    
    #def PayBack (m_algos:abi.Uint64):
       #current_block = ????Global.block+1 ; m_algos=?????
       #pass

    #@external    
    #def LoanExpires ():
        #pass     

    # Add an external method with ABI method signature `hello(string)string`
    @external
    def hello(self, name: abi.String, *, output: abi.String):
        # Set output to the result of `Hello, `+name
        return output.set(Concat(Bytes("Hello, "), name.get()))


def demo():


    # Create an Application client
    
    acc=[s for s in sandbox.get_accounts() if s.address == get_default_algorand_keypair()[1]].pop()
    app_client = client.ApplicationClient(
        # Get sandbox algod client
        client=sandbox.get_algod_client(),
        # Instantiate app with the program version (default is MAX_TEAL_VERSION)
        app=HelloBeaker(version=6),
        # Get acct from sandbox and pass the signer
        signer=acc.signer #pop().signer,
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
    result=app_client.call(HelloBeaker.PayMe, receiver=acc.address)
    print(result.return_value, result.decode_error)
    print((app_client.client.account_info(acc.address)).get('amount'))
    print(acc.address)
    #params = app_client.get_suggested_params() 
    #receiver=app_client.get_application_account_info().address
    #note = "Hello World".encode()
    #amount = 1000000
    #unsigned_txn = transaction.PaymentTxn(app_client.get_sender(), params, receiver, amount, None, note)
    #signed_txn=unsigned_txn.sign(acc.private_key)
    #txid = app_client.send_transaction(signed_txn)
    #print("Successfully sent transaction with txID: {}".format(txid))
    #try:
    #    confirmed_txn = transaction.wait_for_confirmation(app_client, txid, 4)  

    #except Exception as err:
    #    print(err)
    #    return




if __name__ == "__main__":
    demo()