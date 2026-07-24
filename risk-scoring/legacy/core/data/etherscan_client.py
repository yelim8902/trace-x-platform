"""
Etherscan API 클라이언트

실제 블록체인 데이터를 수집하기 위한 Etherscan API 래퍼
"""
from __future__ import annotations

import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import os


class EtherscanClient:
    """Etherscan API 클라이언트 (V2)"""
    
    # V2 API: 통합 base URL 사용
    BASE_URL = "https://api.etherscan.io/v2/api"
    
    # Chain ID 매핑 (V2에서 사용)
    CHAIN_IDS = {
        "ethereum": 1,
        "bsc": 56,
        "polygon": 137,
    }
    
    def __init__(self, api_key: Optional[str] = None, chain: str = "ethereum"):
        """
        Args:
            api_key: Etherscan API 키 (없으면 환경변수에서 읽음)
            chain: 체인 이름 (ethereum, bsc, polygon)
        """
        self.chain = chain.lower()
        self.chain_id = self.CHAIN_IDS.get(self.chain)
        if not self.chain_id:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(self.CHAIN_IDS.keys())}")
        
        # V2 API: 통합 base URL 사용
        self.base_url = self.BASE_URL
        
        # 기본 API 키 (사용자 제공)
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "91FZVKNIX7GYPESECU5PHPZIMKD72REX43")
        if not self.api_key:
            print("Warning: ETHERSCAN_API_KEY not set. Some API calls may fail.")
    
    def get_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        """
        주소의 거래 내역 가져오기
        
        Args:
            address: 주소
            start_block: 시작 블록
            end_block: 종료 블록
            page: 페이지 번호
            offset: 페이지당 결과 수 (최대 10000)
            sort: 정렬 (asc, desc)
        
        Returns:
            거래 리스트
        """
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),  # 최대 10000
            "sort": sort,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_internal_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        """내부 거래(Internal Transactions) 가져오기"""
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "txlistinternal",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),
            "sort": sort,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_token_transfers(
        self,
        address: str,
        contract_address: Optional[str] = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        """ERC-20 토큰 전송 내역 가져오기"""
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),
            "sort": sort,
            "apikey": self.api_key
        }
        
        if contract_address:
            params["contractaddress"] = contract_address
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_balance(self, address: str) -> str:
        """주소의 잔액 조회 (Wei 단위)"""
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1":
            return response.get("result", "0")
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_contract_info(self, address: str) -> Dict[str, Any]:
        """
        컨트랙트 정보 조회 (컨트랙트인지, 토큰인지 등)
        
        Args:
            address: 주소
        
        Returns:
            컨트랙트 정보 (is_contract, is_token 등)
        """
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1":
            result = response.get("result", [{}])[0] if response.get("result") else {}
            source_code = result.get("SourceCode", "")
            
            return {
                "is_contract": bool(source_code),
                "contract_name": result.get("ContractName", ""),
                "compiler_version": result.get("CompilerVersion", ""),
                "is_token": "token" in result.get("ContractName", "").lower() or 
                           "erc20" in source_code.lower() or
                           "erc721" in source_code.lower()
            }
        else:
            return {
                "is_contract": False,
                "contract_name": "",
                "compiler_version": "",
                "is_token": False
            }
    
    def get_address_tags(self, address: str) -> Dict[str, Any]:
        """
        주소의 태그 정보 추출 (Etherscan에서 제공하는 태그 활용)
        
        주의: Etherscan API에는 직접 태그를 가져오는 엔드포인트가 없지만,
        거래 내역과 컨트랙트 정보를 통해 태그를 추론할 수 있습니다.
        
        Args:
            address: 주소
        
        Returns:
            태그 정보 (label, entity_type 등)
        """
        tags = {
            "label": "unknown",
            "entity_type": "unknown",
            "is_contract": False,
            "is_token": False,
            "is_exchange": False,
            "is_mixer": False,
            "is_bridge": False
        }
        
        # 컨트랙트 정보 확인
        contract_info = self.get_contract_info(address)
        tags["is_contract"] = contract_info.get("is_contract", False)
        tags["is_token"] = contract_info.get("is_token", False)
        
        if tags["is_token"]:
            tags["label"] = "token"
            tags["entity_type"] = "token"
        elif tags["is_contract"]:
            tags["label"] = "contract"
            tags["entity_type"] = "contract"
        
        # 알려진 주소 리스트와 매칭
        from core.data.lists import ListLoader
        list_loader = ListLoader()
        
        cex_list = list_loader.get_cex_list()
        mixer_list = list_loader.get_mixer_list()
        bridge_list = list_loader.get_bridge_list()
        
        addr_lower = address.lower()
        
        if addr_lower in mixer_list:
            tags["is_mixer"] = True
            tags["label"] = "mixer"
            tags["entity_type"] = "mixer"
        elif addr_lower in cex_list:
            tags["is_exchange"] = True
            tags["label"] = "cex"
            tags["entity_type"] = "cex"
        elif addr_lower in bridge_list:
            tags["is_bridge"] = True
            tags["label"] = "bridge"
            tags["entity_type"] = "bridge"
        
        # 컨트랙트 이름에서 추가 정보 추론
        contract_name = contract_info.get("contract_name", "").lower()
        if "exchange" in contract_name or "swap" in contract_name:
            tags["is_exchange"] = True
            if tags["label"] == "unknown":
                tags["label"] = "dex"
                tags["entity_type"] = "dex"
        
        return tags
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """API 요청 실행 (Rate limit 고려)"""
        # Rate limit: 5 calls/sec (free tier)
        time.sleep(0.2)  # 5 calls/sec = 0.2초 간격
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # API 에러 메시지 상세 출력
            if result.get("status") == "0" and result.get("message") != "No transactions found":
                error_msg = result.get("message", "Unknown error")
                error_result = result.get("result", "")
                print(f"  ⚠️  Etherscan API Warning: {error_msg}")
                if error_result:
                    print(f"     Details: {error_result}")
            
            return result
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def normalize_transaction(self, tx: Dict[str, Any], chain: str = "ethereum") -> Dict[str, Any]:
        """
        Etherscan 거래 데이터를 표준 형식으로 변환
        
        Args:
            tx: Etherscan API 응답의 거래 데이터
            chain: 체인 이름
        
        Returns:
            표준화된 거래 데이터
        """
        # 타임스탬프 변환
        timestamp = int(tx.get("timeStamp", 0))
        timestamp_iso = datetime.fromtimestamp(timestamp).isoformat() + "Z" if timestamp else ""
        
        # 값 변환 (Wei -> Ether)
        value_wei = int(tx.get("value", 0))
        value_eth = value_wei / 1e18
        
        # USD 변환은 별도로 필요 (현재는 0으로 설정)
        # 실제로는 시세 API를 사용해야 함
        
        return {
            "tx_hash": tx.get("hash", ""),
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "timestamp": timestamp_iso,
            "block_height": int(tx.get("blockNumber", 0)),
            "value_wei": value_wei,
            "value_eth": value_eth,
            "amount_usd": 0.0,  # 시세 API로 변환 필요
            "gas_used": int(tx.get("gasUsed", 0)),
            "gas_price": int(tx.get("gasPrice", 0)),
            "chain": chain,
            "asset_contract": "0xETH",  # Native token
            "is_error": tx.get("isError", "0") == "1",
            "tx_receipt_status": tx.get("txreceipt_status", "1") == "1"
        }


class RealDataCollector:
    """실제 블록체인 데이터 수집기"""
    
    def __init__(self, api_key: Optional[str] = None, chain: str = "ethereum"):
        """
        Args:
            api_key: Etherscan API 키
            chain: 체인 이름
        """
        self.client = EtherscanClient(api_key=api_key, chain=chain)
        self.chain = chain
    
    def collect_address_transactions(
        self,
        address: str,
        max_transactions: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        주소의 모든 거래 내역 수집
        
        Args:
            address: 주소
            max_transactions: 최대 거래 수 (None이면 모두 수집)
        
        Returns:
            표준화된 거래 리스트
        """
        all_transactions = []
        page = 1
        offset = 10000
        
        while True:
            try:
                # 일반 거래
                txs = self.client.get_transactions(
                    address=address,
                    page=page,
                    offset=offset,
                    sort="desc"  # 최신순
                )
                
                if not txs:
                    break
                
                # 표준화
                normalized = [
                    self.client.normalize_transaction(tx, self.chain)
                    for tx in txs
                ]
                
                all_transactions.extend(normalized)
                
                # 최대 거래 수 제한
                if max_transactions and len(all_transactions) >= max_transactions:
                    all_transactions = all_transactions[:max_transactions]
                    break
                
                # 다음 페이지
                if len(txs) < offset:
                    break
                
                page += 1
                
                # Rate limit 고려
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error collecting transactions: {e}")
                break
        
        return all_transactions
    
    def collect_high_risk_addresses(
        self,
        addresses: List[str],
        max_transactions_per_address: int = 100
    ) -> List[Dict[str, Any]]:
        """
        여러 주소의 거래 내역 수집 (고위험 주소 우선)
        
        Args:
            addresses: 주소 리스트
            max_transactions_per_address: 주소당 최대 거래 수
        
        Returns:
            모든 거래 리스트
        """
        all_transactions = []
        
        for i, address in enumerate(addresses):
            print(f"Collecting {i+1}/{len(addresses)}: {address}")
            
            try:
                txs = self.collect_address_transactions(
                    address=address,
                    max_transactions=max_transactions_per_address
                )
                all_transactions.extend(txs)
                
                # Rate limit 고려
                time.sleep(1)
                
            except Exception as e:
                print(f"Error collecting from {address}: {e}")
                continue
        
        return all_transactions


# 사용 예시
if __name__ == "__main__":
    # API 키 설정 (환경변수 또는 직접 입력)
    API_KEY = os.getenv("ETHERSCAN_API_KEY", "YOUR_API_KEY_HERE")
    
    # 클라이언트 생성
    collector = RealDataCollector(api_key=API_KEY, chain="ethereum")
    
    # 주소의 거래 내역 수집
    address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"  # 예시 주소
    transactions = collector.collect_address_transactions(
        address=address,
        max_transactions=100
    )
    
    print(f"수집된 거래 수: {len(transactions)}")
    if transactions:
        print(f"첫 거래: {transactions[0]}")

