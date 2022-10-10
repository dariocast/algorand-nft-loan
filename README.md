# Group 3 
- Capocasale Vittorio
- Castellano Dario
- Renieri Margherita
- Toffalini Alessandro

# Algorand NFT Loan System

## Goal of the project
The problem identified is the access to liquidity in terms of cryptocurrency or specific assets that could be addressed with a loan mechanism of owned NFT.

## Smart contract specifications
The smart contract is able to accept an NFT from an account (borrower) for a period of time, storing info on the global state. During this period other accounts (lenders) are able to bid in ALGO for that NFT. At any time during this initial period, the borrower can interact with the contract to get back the NFT (in this case the bidded amount returns to the lender) or to accept the loan. In the second case, there is a predefined period of time in which the borrower must repay the loan to the lender, otherwise, after the deadline, the lender can obtain the NFT by interacting with the contract.
So, we have two different roles:
- The Borrower (B)
- The Lender (L)

The Stateful Smart Contract stores the following information:
	
	- NFT_ID (a handle to retrieve the correct NFT)
	- borrower_address (the address of the borrower)
	- lender_address (current bidder)
	- n_Algos (highest bid)
	- loan_threshold (auction staring amount)
	- auction_period (number of blocks from the offer creation)
	- payback_deadline (number of blocks from the bid acceptance)
	- last_interest_update_block (starting block to compute the interest. It stores the block corresponding to the last successful invocation of PayBack)
	- debt_left (The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block)))

The smart contract supports the following operations.

Offer (NFT, borrower_address, loan_threshold, auction_deadline, payback_deadline)

B sends the NFT to the smart contract. B establishes a minimum loan threshold (loan_threshold), the number of blocks of the auction validity period (auction_period), and the loan payback deadline (payback_deadline), which is the number of blocks from when AcceptBid is invoked. The smart contract stores B's address (borrower_address) for future ownership transfers.


Bid (lender_address, n_Algos)

Bid is invokable only during the auction validity period. L sends some Algos (n_Algos) to the smart contract. The smart contract stores the lender's address (lender_address). The amount of Algos must be greater than the loan threshold and the current highest bid. The smart contract refunds the previous highest bid and replaces it with the new bid.


AcceptBid ()

AcceptBid is invokable only by B. The smart contract forwards n_Algos to B. The smart contract still owns the NFT. CancelOffer and Timeout can no longer be invoked.


Timeout ()

Timeout is invokable only after the auction ends and if AcceptBid is not invoked.  
Anyone can invoke Timeout to return the managed assets (NFT, n_Algos) to their original owners. 


CancelOffer ()

Only B can invoke CancelOffer, and only if AcceptBid is not invoked. The smart contract returns the managed assets (NFT, n_Algos) to their original owners. 


PayBack (m_Algos, current_block)

B gives some Algos (m_Algos) to the smart contract. PayBack updates the current debt by summing the accumulated compound interest. m_Algos must repay at least the accumulated compound interest. If m_Algos exceeds B's current debt, the smart contract returns the exceeding Algos to B. The smart contract subtracts m_Algos from B's debt. The smart contract keeps the portion of the m_Algos entitled to the smart contract creators and forwards the remaining part to L. If B's debt goes to 0, the smart contract gives the NFT back to B. PayBack can be invoked after the payback deadline expires but not after LoanExpired is invoked.


LoanExpired ()

LoanExpired can be invoked only by L after the payback deadline expires. L receives the NFT from the smart contract. PayBack cannot be invoked anymore.


PayMe (creator_address)

PayMe can only be invoked by the creator(s) of the smart contract. PayMe sends the currently collected fees to the creator's address.




## State of the art  
Over the last years, it was found that an increased number of cryptocurrency projects focused on building financial primitives for the NFT space. One of them are the lending platforms where users can borrow fungible tokens by collateralizing the loan with their NFT.

The main  platforms are:
* **PINE**: Its lending protocol allows borrowers to borrow fungible digital tokens from lenders using non-fungible tokens as collateral. Lenders earn yield on tangible digital assets, acquire NFT assets at a discount and segregated pool structure for better market and compliance risk management. Borrowers obtain instant permissionaless loans with no back-and-forth needed with lenders and have flexibility to repay loan early or to extend loan via rollover.
Every lender sets up their own segregated lending pool giving flexibility to choose the types of collateral they want to lend and set specific terms (such as loan fixed duration and interest rates). In case of default, the ownership of the NFT is transferred to the lender. 
Pine.loans is a platform for lenders to list the loan offers, allows NFT owners to get loans with the best conditions and guarantees enforceability of the terms of the loans.
The platform offers a portal where lenders are able to manage their segregated pools, their offers and collateral repossession.
* **TrustNFT**: It is a platform powered by the MVP, an NFT Evaluation Machine which is powered by AI and big data. The platform uses data sources from the blockchain and establishes trends in the NFT and cryptocurrency markets.
TrustNFT is a peer-to-peer platform for NFT-collateralized loans that enables borrowers to put up assets for loans and lenders to make offers to lend in return for interest.
* **Taker**: It is a liquidity protocol which uses NFT assets as the starting point to provide lending services for all kinds of novel crypto assets of the future. It will be the first NFT loan protocol that supports Uniswap V3 LP tokens. It increases the liquidity for NFT assets and improves the efficiency of NFT lending and borrowing services.
The protocol removes the requirement for oracles by locking price and peer-to-peer quoting. Both borrower and lender obtain incentives in the form of ecosystem tokens as rewards.
* **Arcade**: It is a Web3 platform that provides a liquid lending market for NFTs. It is an innovative peer to peer lending platform that enables NFT owners to unlock liquidity on single NFT or multiple NFTs on Ethereum. Lenders (holding stablecoins or ERC20 tokens) underwrite loans collateralized by borrowers’ NFTs.
* **Liquid NFTs**
* **Fluid NFTs**
* **JPEG’d**

## Technical challenges 
The possibility to apply economics concept to the loan (i.e. interests).

The possibility to receive specific assets instead of ALGOs.

Smart contract manages group of transactions so it has to be accurate in the evaluation of them.

In order to perform the payback it should use an inner payment transaction to the bidder.

The temporal parameters has to be calculated in terms of blockchain round.

NFT is an Algorand Standard Asset with specific configuration described in the [ARC-0003](https://arc.algorand.foundation/ARCs/arc-0003) .

## Futures and business value
The NFTs loan systems are geining increasing attention because they allow users to access to liquidity simply owning NFTs. A marketplace of this kind of contract on algorand could allow the interoperability between the NFT marketplace and DEFI.
Even more, with algorand state proof this system may interact with other blockchain.

## Future developments
The initial idea involves two key players, a user who owns an NFT and would like to use it as collateral to access credit. And a counterparty willing to buy the NFT at a predefined price (chosen as the winner of an auction) who grants the minimum price in ALGO, all in exchange for repaying the loan in installments with a specified time interval and interest rate. One of the possible future developments is to enlarge the pool of potential lenders by considering splitting the NFT into several components. So that subsequently a community willing to lend cryptocurrency in exchange for fractional participation in the ownership of an NFT in case of default and alternatively the interest rate charged. 
Another potential development is the use of stablecoin instead of classic cryptocurrencies, so that lending can be even more easily transformed into fiat currency.
