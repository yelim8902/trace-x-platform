import threading
import time
import requests
from typing import Dict, Any, List

class EtherscanV2Client:

    BASE_URL = "https://api.etherscan.io/v2/api"

    # 무료 티어 실측 한도가 에러 메시지에 "3/sec"로 찍힘(공식 문서상 5/sec보다 낮게
    # 걸림) - 안전 마진을 두고 초당 3회로 제한
    MIN_REQUEST_INTERVAL_SEC = 1.0 / 3.0
    MAX_RETRIES = 4
    RETRY_BACKOFF_BASE_SEC = 1.0

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self._rate_lock = threading.Lock()
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        """이 프로세스 안에서 순차적으로 Etherscan 호출 간격을 강제한다.
        gunicorn 워커가 여러 개면 워커별로 별도 인스턴스가 생겨 완벽한
        전역 제한은 아니지만(프로세스 간 공유 안 됨), 단일 요청 안에서
        벌어지는 멀티홉 BFS의 폭주(수백~수천 콜)를 막는 게 핵심 목적이라
        이 정도로 충분함."""
        with self._rate_lock:
            now = time.monotonic()
            wait = self.MIN_REQUEST_INTERVAL_SEC - (now - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def _make_request(self, params: Dict[str, Any], chain_id: int = 1) -> Dict[str, Any]:
        params['apikey'] = self.api_key
        params['chainid'] = chain_id  # V2 requires chainid parameter

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            self._throttle()
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get('status') == '0' and data.get('message') == 'NOTOK':
                    error_result = data.get('result', 'Unknown error')
                    if 'rate limit' in str(error_result).lower() and attempt < self.MAX_RETRIES - 1:
                        # 레이트리밋은 일시적 오류이므로 지수 백오프 후 재시도
                        time.sleep(self.RETRY_BACKOFF_BASE_SEC * (2 ** attempt))
                        last_error = Exception(f"Etherscan API Error: {error_result}")
                        continue
                    raise Exception(f"Etherscan API Error: {error_result}")

                return data
            except requests.exceptions.RequestException as e:
                last_error = Exception(f"Etherscan API request failed: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BACKOFF_BASE_SEC * (2 ** attempt))
                    continue
                raise last_error

        raise last_error
    
    def get_normal_transactions(
        self,
        chain_id: int,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        result = self._make_request(params, chain_id)
        return result.get('result', [])
    
    def get_erc20_transfers(
        self,
        chain_id: int,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc',
        contractaddress: str = None
    ) -> List[Dict[str, Any]]:
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        if contractaddress:
            params['contractaddress'] = contractaddress
        
        result = self._make_request(params, chain_id)
        return result.get('result', [])
    
    def get_internal_transactions(
        self,
        chain_id: int,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        result = self._make_request(params, chain_id)
        return result.get('result', [])
    
    def get_balance(self, chain_id: int, address: str) -> str:
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest'
        }
        
        result = self._make_request(params, chain_id)
        return result.get('result', '0')
