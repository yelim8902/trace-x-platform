from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from src.api.etherscan_v2 import EtherscanV2Client

from src.enums.tx_types_enum import TxTypesEnum as TxTypes
from src.enums.methods_enum import MethodsEnum as Methods
from src.enums.bridges_enum import BridgesEnum as Bridges

from src.bridges import debridge, usdt0

from src.constants.bridge_methods import METHODS as BRIDGE_METHODS
from src.constants.swap_methods import METHODS as SWAP_METHODS
from src.constants.rpc_urls import URLS as RPC_URLS
from src.constants.token_addresses import USDT_ADDRESS
from src.types.graph import Graph
from src.types.scoring_graph import ScoringGraph
from src.utils.token.services import get_token_price

from web3 import Web3

NATIVE_TOKEN_DECIMALS = 18
DEFAULT_START_BLOCK = 0
DEFAULT_END_BLOCK = 99999999

class Analyzer:
    def __init__(self, api_key: str):
        self.scanner = EtherscanV2Client(api_key=api_key)

    def get_fund_flow_by_address(self, chain_id: int, address: str) -> Dict[str, Any]:
        graph = Graph()
        normal_txs, erc20_txs = self._fetch_txs_parallel(chain_id, address)
        for tx in normal_txs + erc20_txs:
            self._add_nodes_from_tx(graph=graph, chain_id=chain_id, tx=tx)
            self._add_edge_from_tx(graph=graph, chain_id=chain_id, tx=tx)
        return graph.to_dict()

    def analyze_bridge_transaction(self, chain_id: int, tx_hash: str) -> Dict[str, Any]:
        url = RPC_URLS[str(chain_id)]
        w3 = Web3(Web3.HTTPProvider(url))

        result = w3.eth.get_transaction(transaction_hash=tx_hash)
        input_data = result['input']
        methodId = input_data[:10]

        bridge = BRIDGE_METHODS[methodId]['label']
        if bridge == 'DeBridge':
            dst_chain_id, recipient = debridge.decode_bridge_transaction(tx_hash=tx_hash)
        elif bridge == 'USDT0':
            dst_chain_id, recipient = usdt0.decode_bridge_transaction(tx_hash=tx_hash, chain_id=chain_id)
        else:
            raise NotImplementedError(f"Bridge protocol '{bridge}' not yet implemented")

        return self.get_fund_flow_by_address(chain_id=dst_chain_id, address=recipient)

    def get_multihop_fund_flow_for_scoring(
        self,
        chain_id: int,
        address: str,
        max_hops: int = 1,
        max_addresses_per_direction: int = 10
    ) -> Dict[str, Any]:
        graph = ScoringGraph()
        visited_addresses = set()

        main_address = address.lower()
        current_hop_addresses = {main_address}

        for hop in range(max_hops):
            next_hop_addresses = set()

            for current_address in current_hop_addresses:
                if current_address in visited_addresses:
                    continue

                visited_addresses.add(current_address)

                connected_addresses = self._get_fund_flow_for_scoring(
                    graph=graph,
                    chain_id=chain_id,
                    address=current_address
                )

                next_hop_addresses.update(connected_addresses)

            # max_addresses_per_direction을 실제로 적용 — 안 그러면 활동 많은
            # 주소(거래소 핫월렛 등)에서 홉마다 연결 주소 수가 기하급수적으로
            # 불어나 Etherscan 호출이 수백~수천 건으로 폭주함
            if len(next_hop_addresses) > max_addresses_per_direction:
                next_hop_addresses = set(
                    sorted(next_hop_addresses)[:max_addresses_per_direction]
                )

            current_hop_addresses = next_hop_addresses

            if not current_hop_addresses:
                break

        return graph.to_dict()

    def _get_fund_flow_for_scoring(
        self,
        graph: ScoringGraph,
        chain_id: int,
        address: str
    ) -> set[str]:
        connected_addresses = set()
        address_lower = address.lower()

        normal_txs, erc20_txs = self._fetch_txs_parallel(chain_id, address)

        for txs, label in [(normal_txs, 'normal'), (erc20_txs, 'erc20')]:
            if isinstance(txs, Exception):
                print(f"Error fetching {label} txs for {address}: {txs}")
                continue
            for tx in txs:
                from_addr = tx.get('from', '').lower()
                to_addr = tx.get('to', '').lower()
                self._add_nodes_from_tx(graph=graph, chain_id=chain_id, tx=tx)
                self._add_edge_from_tx(graph=graph, chain_id=chain_id, tx=tx)
                if to_addr == address_lower and from_addr:
                    connected_addresses.add(from_addr)
                if from_addr == address_lower and to_addr:
                    connected_addresses.add(to_addr)

        return connected_addresses

    def _fetch_txs_parallel(self, chain_id: int, address: str):
        with ThreadPoolExecutor(max_workers=2) as executor:
            normal_future = executor.submit(self._fetch_normal_txs, chain_id=chain_id, address=address)
            erc20_future = executor.submit(self._fetch_erc20_transfers, chain_id=chain_id, address=address)
            try:
                normal_txs = normal_future.result()
            except Exception as e:
                normal_txs = e
            try:
                erc20_txs = erc20_future.result()
            except Exception as e:
                erc20_txs = e
        return normal_txs, erc20_txs

    def _add_nodes_from_tx(self, graph, chain_id: int, tx: Dict[str, Any]) -> None:
        for address in [tx['from'], tx['to']]:
            graph.add_node(address, chain_id)

    def _add_edge_from_tx(self, graph, chain_id: int, tx: Dict[str, Any]) -> None:
        token_symbol = tx.get('tokenSymbol')
        action = "tokentx" if token_symbol else "txlist"

        tx_type = self._classify_tx_type(tx=tx, action=action)
        if tx_type == TxTypes.UNKNOWN:
            return

        amount = int(tx['value'])
        token_address = ''
        block_height = int(tx['blockNumber'])
        usd_value = 0

        if tx_type == TxTypes.NATIVE:
            amount_float = amount / 10 ** NATIVE_TOKEN_DECIMALS
            amount = str(amount_float)
            token_symbol = 'ETH'
            try:
                eth_price_data = get_token_price("ETH")
                usd_value = amount_float * eth_price_data["price"] if eth_price_data else amount_float * 2000
            except Exception as e:
                print(f"Warning: Failed to get ETH price: {e}")
                usd_value = amount_float * 2000
        elif tx_type == TxTypes.ERC20_TRANSFER:
            decimals = int(tx['tokenDecimal'])
            amount_float = amount / 10 ** decimals
            amount = str(amount_float)
            token_address = tx['contractAddress']
            token_symbol = tx.get('tokenSymbol', 'UNKNOWN')
            try:
                token_price_data = get_token_price(token_symbol)
                usd_value = amount_float * token_price_data["price"] if token_price_data else 0
            except Exception as e:
                print(f"Warning: Failed to get {token_symbol} price: {e}")
        elif tx_type in (TxTypes.BRIDGE, TxTypes.SWAP):
            amount = str(amount)

        graph.add_edge(
            chain_id=chain_id,
            tx_hash=tx['hash'],
            block_height=block_height,
            from_address=tx['from'],
            to_address=tx['to'],
            amount=amount,
            timestamp=tx['timeStamp'],
            token_address=token_address,
            token_symbol=token_symbol,
            usd_value=usd_value,
            tx_type=tx_type
        )

    def _fetch_normal_txs(self, chain_id: int, address: str) -> list:
        return self.scanner.get_normal_transactions(
            chain_id=chain_id,
            address=address,
            startblock=DEFAULT_START_BLOCK,
            endblock=DEFAULT_END_BLOCK,
            sort='desc'
        )

    def _fetch_erc20_transfers(self, chain_id: int, address: str) -> list:
        return self.scanner.get_erc20_transfers(
            chain_id=chain_id,
            address=address,
            startblock=DEFAULT_START_BLOCK,
            endblock=DEFAULT_END_BLOCK,
            sort='desc'
        )

    def _classify_tx_type(self, tx: Dict[str, Any], action: str) -> str:
        input_data = tx['input']
        method_id = tx['methodId']
        function_name = tx.get('functionName', '').lower()

        if action == "tokentx":
            if tx.get('contractAddress') and tx.get('tokenSymbol'):
                return TxTypes.ERC20_TRANSFER
        elif action == "txlist":
            if input_data == '0x':
                return TxTypes.NATIVE

        if method_id in SWAP_METHODS or 'swap' in function_name:
            return TxTypes.SWAP
        elif method_id in BRIDGE_METHODS:
            return TxTypes.BRIDGE
        elif int(tx.get('value', '0')) > 0:
            return TxTypes.NATIVE

        return TxTypes.UNKNOWN
