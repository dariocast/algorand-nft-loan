# Group 3 
- Capocasale Vittorio
- Castellano Dario
- Renieri Margherita
- Toffalini Alessandro

# Algorand NFT Loan System

## Environment setup

Create the development environment:
1. Connect to a network
    * **Using Sandbox**
      * Make sure the docker daemon is running and the docker-compose is correctly installed
      * If you do not have the `sandbox` cloned, follow the [Sandobox](https://github.com/algorand/sandbox) installation guidelines otherwise go to the next step (launch it). 
      * Launch `sandbox` with `./sendbox up dev`
    * **Using Testnet**
      * Create an account on [PureStake](https://www.purestake.com/) and get an API key
      * Export in the environment the following variables:
        * `ALGOD_TOKEN` with your Purestake API key
        * `ALGOD_ADDRESS` with the address of the Purestake testnet algod
2. Clone the repo
3. Check your python version is `>= 3.10`. Verify it with the `python --version`
4. Create the Virtual Environment
    * `pip3 install virtualenv`
    * `virtualenv venv`
    * `source venv/bin/activate`
    * `pip3 install pyteal py-algorand-sdk`
5. Test the environment with https://developer.algorand.org/docs/sdks/python/
6. Install all the required packages
    * `pip install -r requirements.txt`

## Goal of the project

The project aims to provide liquidity in terms of cryptocurrency or specific assets that could be addressed with a loan mechanism of owned NFT.

### Use case

The developed system could be associated to the real scenario pawnshop.

## Smart contract specifications

 In the NFT loan developed, there are three different roles:
- The Contract Owner (CO) that creates and inizialize the contract
- The Lender (L) that provides assets to the smart contract
- The Borrower (B) that provides her NFT as collaterla to borrow cryptocurrency.

Once the *contract owner* created the smart contract, it is able to accept an NFT from an account - *borrower* - for a period of time and stores info on the global state. During this period other accounts - *lenders* - are able to bid in ALGO for that NFT. At any time during this initial period, the borrower can interact with the contract to get back the NFT (in this case the bidded amount returns to the lender) or to accept the loan.

In the second case, there is a predefined period of time in which the borrower must repay the loan to the lender, otherwise, after the deadline, the lender can obtain the NFT by interacting with the contract.

The Stateful Smart Contract stores the following information:
	
	- nft_id (a handle to retrieve the correct NFT)
	- borrower_address (the address of the borrower)
	- lender_address (current highest bidder)
	- highest_bid (highest bid)
	- auction_base (auction staring amount)
	- auction_period (auction deadline block number. The client submits a duration, the contract computes the deadline)
	- payback_deadline (loan deadline. It initially stores the duration. It is calculated after the accept_offer is invoked)
	- last_interest_update_block (starting block to compute the interest. It stores the block corresponding to the last successful invocation of pay_back)
	- debt_left (current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block)))
	- state (current contract state)

The smart contract supports the following operations:
- `provide_access_to_nft(borrower_address, NFT, n_Algos)`

`provide_access_to_nft` is sent by B to the smart contract to trigger the NFT optin.

- `set_offer (borrower_address, NFT, auction_base, auction_period, payback_deadline)`

B sends the NFT to the smart contract. B establishes a minimum loan threshold (`auction_base`), the number of blocks of the auction validity period (`auction_period`), and the loan payback deadline (`payback_deadline`), which is the number of blocks from when `accept_bid` is invoked. The smart contract stores B's address (`borrower_address`) for future ownership transfers.

- `place_bid (lender_address, n_Algos)`

`place_bid` is invokable only during the auction validity period. L sends some Algos (`n_Algos`) to the smart contract. The smart contract stores the lender's address (`lender_address`). The amount of Algos must be greater than the loan threshold and the current highest bid. The smart contract refunds the previous highest bid and replaces it with the new bid.

- `accept_bid ()`

`accept_bid` is invokable only by B. The smart contract keeps a small percentage of the `n_Algos` and forwards the remaining part to B. the percentage represents a service fee that CO can collect by invoking the `pay_me` function. The smart contract still owns the NFT. `cancel_offer` and `timeout` can no longer be invoked.

- `timeout ()`

`timeout` is invokable only after the auction ends and if `accept_bid` is not invoked.  
Anyone can invoke timeout to return the managed assets (`NFT, n_Algos`) to their original owners. 

- `cancel_offer ()`

Only B can invoke `cancel_offer`, and only if `accept_bid` is not invoked. The smart contract returns the managed assets (`NFT, n_Algos`) to their original owners. 

- `pay_back (borrower_address, m_Algos)`

B gives some Algos (`m_Algos`) to the smart contract. `pay_back` updates the current debt by summing the accumulated interest. `m_Algos` must repay at least the accumulated compound interest.

If `m_Algos` exceeds B's current debt, the smart contract returns the exceeding Algos to B. The smart contract subtracts `m_Algos` from B's debt. The smart contract forwards the the `m_Algos` to L.

If B's debt goes to 0, the smart contract gives the NFT back to B. `pay_back` can be invoked after the loan payback deadline expires but not after `loan_expired` is invoked.

- `loan_expired ()`

`loan_expired` can be invoked only by L after the loan payback deadline expires. L receives the NFT from the smart contract. `pay_back` cannot be invoked anymore.

- `pay_me (creator_address)`

`pay_me` can only be invoked by the creator of the smart contract. `pay_me` sends the currently collected fees to the creator's address.



## State of the art  

Public attention towards NFTs has rapidly risen in 2021, when NFT market has experienced record sales.
In just one year, it has been [shown](https://www.mdpi.com/2227-7390/10/3/335) that NFT market increased from total daily sales of about USD 183,121 in 2020 to an average of USD 38 million at the [end of 2021]( https://nonfungible.com/market/).
According to [DappRadar](https://dappradar.com/blog/), the third quarter of 2022 saw USD 3.4 billion in NFT sales. From the current trend, it is evident that the digital asset market will be as big as or even bigger than the physical asset market in the long run. In relation to this, over the last years, it was found that an increased number of cryptocurrency projects focused on building financial primitives for the NFT space.
One of them are the lending platforms where users can borrow fungible tokens by collateralizing the loan with their NFT. 
NFT lending platforms allow users to borrow liquid assets by using their NFTs as collateral. 
It is possible to distinguish three types of lending pool approaches: peer to peer, peer to pool, and collateralized debt position (CDP).
Starting from them, we are going to illustrate their mechanisms and provide examples of some platforms.
1. **Peer to peer**: This is the main scenario that enables individuals to borrow and lend money directly from one to another. These platforms have similar behaviours.
One of these is that the NFTs are locked as collateral in contract, then the lender provides a loan to the borrower within a specific time frame. 
Another takes into account the lending process which involves an auction on the loan’s interest rate. In general lenders who provide the lowest interest rates win the bids.
The main benefit of the P2P lending is that it is perfect for covering NFTs risks. This kind of lending is characterized by combinations of high interest rates and moderate loan-to-value ratios.
Platforms that use this approach are:
	* [**NFTfi**](https://www.nftfi.com/), (2022): It is a peer-to-peer interaction among borrowers and lenders. Borrowers use their NFTs as collateral to get liquidity by the lenders that give back wETH or DAI. The system enables changes to loan settings (market conditions, life circumstances, lending/borrowing strategies, etc.). In addition, a loan can be renegotiated by the borrower or the lender. It can be triggered any time during an active loan or after the loan has expired (before the lender forecloses the loan).
	* [**TrustNFT‌**](https://info-87.gitbook.io/trustnft-light-paper/), (2021): The main characteristic of the platform  is the accurate evaluation provided by an NFT Evaluation Machine which is powered by AI and big data. The platform uses data sources from the blockchain and establishes trends in the NFT and cryptocurrency markets. It is a peer-to-peer platform for NFT-collateralized loans that enables borrowers to put up assets for loans and lenders to make offers to lend in return for interest. Once the borrower picks her NFT,  the platform evaluates the maximum borrow limit for the asset(s). Following this, there is an agreement phase and then the asset is locked in a TrustNFT smart contract until the loan is completely repaid.
	* [**Pawnfi‌**](https://pawnfi.com/), (2020): The Pawnfi protocol proposes the concept of Non-Standard Assets (NSA) that can be fungible and non-fungible (such as NFTs, LP Tokens, Fungible tokens with liquidity, tokenized insurance, bonds, bills, derivatives, long-tail assets). Owners of these assets can draw loans against or lease their assets to gain instant usage from their illiquid tokens by placing them on Pawnfi. The system has three modes: pawn (collateral for loans), lease (lending the assets to others for passive income) and sale (listing on secondary markets for the highest bid).
	* [**Yawww‌**](https://yawww.gitbook.io/whitepaper/), (2021): It is the first Solana's P2P automated escrow & trading service for NFTs and Solana's P2P loans marketplace. According to its protocol, every owner of Solana NFTs (borrowers) can create a loan request on Yawww using her NFT as collateral and setting loan amount, interest rate, and duration. Anybody can fund the loan with a single click, or they want to negotiate the terms.
	* [**Arcade‌**](https://docs.arcade.xyz/docs), (2021): The system allows users to wrap multiple NFTs into one wrapped NFT that can be collateralized as a single asset. NFT price movements depend on the floor price and the value of ETH. If the value of the NFTs is lower than the borrowed coins, lenders might be at the loss, and not be able to sell the NFTs at the market price in case of late payment.
2. **Peel to pool/peer-to-protocol**: This kind of system takes into account NFTs lending borrowing liquidity directly from the protocol. The main actors in this scenario are the liquidity providers and the borrowers. The former deposits into the protocol pools while the latter get liquidity after collateralizing their NFTs which are locked in the protocol’s smart digital vaults.
Platforms that use this approach are:
	* [**NFTuloan**](https://www.nftuloan.com/index.php), (2021): It is a liquidity pool provider for digital arts, domain names, collectibles, gaming cards, trading cards, virtual lands, utilities. Once the user has added her crypto wallet to the platform, she can apply for loans using her NFTs as collateral. Each loan has a fixed payback duration of 1 hour to 30 days, and the flexible interest rate which depends on the NFT. value. Moreover, NFTuloan provides an instant NFT estimation feature in order to guarantee accurate, transparent, and fair valuations of the token.
	* [**BendDAO**](https://docs.benddao.xyz/portal/), (2021):  It is an NFT liquidity protocol that supports instant NFT-backed loans, Collateral Listing, and NFT Down Payment. In BendDAO, NFT holders can borrow ETH through the lending pool using NFTs as collateral instantly, while depositors provide ETH liquidity to earn interest. To minimize the losses caused by the market fluctuations, the borrower has a 24-hour liquidation protection period to pay back the loan (including interests). All the collateral are directly listed on the DBendDAO. Moreover, NFT holders can choose to get up to 40% of the floor value of the listing before it even sells. The instant liquidity is provided by the instant NFT-backed loan. The balance after deducting debt with interests will be transferred to the borrower after the deal. 
	* [**PINE**](https://docs.pine.loans/introduction/overview), (2022): Its lending protocol allows borrowers to borrow fungible digital tokens from lenders using non-fungible tokens as collateral. Lenders earn yield on tangible digital assets, acquire NFT assets at a discount and segregated pool structure for better market and compliance risk management. Borrowers obtain instant permissionaless loans with no back-and-forth needed with lenders and have flexibility to repay loan early or to extend loan via rollover. Every lender sets up their own segregated lending pool giving flexibility to choose the types of collateral they want to lend and set specific terms (such as loan fixed duration and interest rates). In case of default, the ownership of the NFT is transferred to the lender. Pine.loans is a platform for lenders to list the loan offers, allows NFT owners to get loans with the best conditions and guarantees enforceability of the terms of the loans.The platform offers a portal where lenders are able to manage their segregated pools, their offers and collateral repossession.
3. **Collateralized Debt Position**: It is a new model for the NFT collateralized currency market which lets borrowers take out the stablecoin DAI when they collateralize ETH. It is created when collateral is locked into MakerDAO’s smart contract and the decentralized stablecoin DAI is generated. The value of the collateral placed in the CDP exceeds 150% of the generated DAI value. In undercollateralized scenario, the assets in the smart contract are sold and the funds are used to repay the generated DAI, a 13% liquidation penalty, and the stability fees applicable at the time of payment. DAI, an Ethereum-based ERC-20-compatible token, are a decentralized loan and  is backed by the collateral’s value. If the borrower wants to unlock the collateral, she has to repay the DAI (and other stability fees). 
A platforms that uses this approach is:
	* [**JPEG’d**](https://docs.jpegd.io/about-the-lending-protocol/introduction), (2022): It is a decentralized lending protocol on the Ethereum blockchain that enables NFT holders to open CDPs using their NFTs as collateral. Users mint PUSd (native stablecoin of the protocol) or pETH (native Ethereum derivative of the protocol) allowing them to obtain leverage on their NFTs. JPEG'd uses a peer to protocol lending mechanism and borrowers can set up several options during the lending step. PUSd  gets minted against every borrow position at a fixed borrow rate (2%) and burned upon closing of the position. All debt positions allow 32% of the collateral value to be drawn and liquidation occurs whether the debt/collateral ratio is 33% or higher.

## Technical challenges 

The development of the project led to face and manage several technical challenges:
- the NFT, Algorand Standard Asset with its specific configuration described in the [ARC-0003](https://arc.algorand.foundation/ARCs/arc-0003).
- economics concept to the loan (i.e. interests).
- the receive Any Standard Assets as collateral.
- the splitting of the payback borrower's debt with a interest that is calculated on the portion of the unpaid debt.
- group of transactions in order to have a more accurate assessment of them.
- the use of an inner payment transaction to the bidder to perform the payback.
- temporal parameters has to be calculated in terms of blockchain round. This led to some issue in Testnet already raised to the algorand repository that as been solved pushing arbitrary round number when needed.
- the reproduction a reusable smart contract using the concept of state, so the same contract can be used multiple times without recreating the app. This is a gain for the contract owner.
- different scenarios.
- minumum balance which dynamic optins.
- inner transactions with 0 fee.

### Qualitative discussion of security and correctness 

All the input data have been checked in terms of security and correctness.

### Potential business benefits 

The developed scenario provides a profitable solution for all the users that are involved:
- the borrower obtains her loan
- the lender has an annual interest rate 
- the contract owner has an interest rate for each contract created 

The interaction among the users is transparent and the guaranteed by the predefined smart contract.  

## Futures and business value

The NFTs loan systems are gaining increasing attention because they allow users to access to liquidity simply owning NFTs. A marketplace of this kind of contract on Algorand could allow the interoperability between the NFT marketplace and DeFi.
Even more, with Algorand state proof this system may interact with other blockchain.

The initial idea involves two key players:
- a user who owns an NFT and would like to use it as collateral to access credit
- a counterparty willing to buy the NFT at a predefined price (chosen as the winner of an auction) who grants the minimum price in ALGO, all in exchange for repaying the loan in installments with a specified time interval and interest rate.

There are several improvements that could be developed starting from the current scenario.
One of the possible future developments is to enlarge the pool of potential lenders by considering splitting the NFT into several components. So that subsequently a community willing to lend cryptocurrency in exchange for fractional participation in the ownership of an NFT in case of default and alternatively the interest rate charged. 
Another potential progress is the use of stablecoin instead of classic cryptocurrencies, so that lending can be even more easily transformed into fiat currency.
