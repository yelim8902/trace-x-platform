"""
데모용 주소 분석 API (Stage 1 + Stage 2 통합)
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from core.scoring.stage2_scorer import Stage2Scorer
from core.data.etherscan_client import EtherscanClient, RealDataCollector
from core.data.lists import ListLoader
import pandas as pd
import networkx as nx
import time

demo_analysis_bp = Blueprint("demo_analysis", __name__)


def _calculate_address_stats(address: str, transactions: List[Dict[str, Any]], graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """IKNA 스타일 주소 통계 계산"""
    address_lower = address.lower()
    
    # 금융 통계
    total_received = 0.0
    total_sent = 0.0
    incoming_count = 0
    outgoing_count = 0
    
    # 시간 통계
    timestamps = []
    
    for tx in transactions:
        from_addr = str(tx.get("from", "")).lower().strip()
        to_addr = str(tx.get("to", "")).lower().strip()
        
        # 값 계산: USD 우선, 없으면 Wei를 ETH로 변환 후 대략적 USD 추정
        value_usd = tx.get("usd_value", 0) or tx.get("amount_usd", 0)
        if value_usd == 0:
            # Wei 값을 ETH로 변환
            value_wei = tx.get("value", 0) or tx.get("value_wei", 0)
            if isinstance(value_wei, (int, float)) and value_wei > 0:
                value_eth = value_wei / 1e18
                # ETH 가격을 대략적으로 2000 USD로 추정 (실제로는 시세 API 사용 필요)
                value_usd = value_eth * 2000.0
        else:
            value_usd = float(value_usd)
        
        timestamp = tx.get("timestamp", 0)
        if timestamp:
            # timestamp가 문자열이면 정수로 변환
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except:
                    timestamp = 0
            if timestamp > 0:
                timestamps.append(timestamp)
        
        # 주소 매칭 (정확히 비교)
        if to_addr == address_lower:
            total_received += value_usd
            incoming_count += 1
        if from_addr == address_lower:
            total_sent += value_usd
            outgoing_count += 1
    
    # Balance 계산 (간단한 추정)
    balance = total_received - total_sent
    
    # 시간 정보
    first_usage = min(timestamps) if timestamps else None
    last_usage = max(timestamps) if timestamps else None
    
    # 그래프 통계
    graph_stats = graph_data.get("graph_stats", {})
    total_nodes = graph_stats.get("total_nodes", 0)
    total_edges = graph_stats.get("total_edges", 0)
    hop1_count = graph_stats.get("hop1_count", 0)
    
    # 엔티티 정보 (간단한 추론)
    entity_name = None
    entity_type = "Unknown"
    
    # 알려진 주소 체크
    known_addresses = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {"name": "Uniswap", "type": "DEX"},
        "0xe592427a0aece92de3edee1f18e0157c05861564": {"name": "Uniswap V3", "type": "DEX"},
        "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": {"name": "Binance", "type": "Exchange"},
    }
    
    if address_lower in known_addresses:
        entity_info = known_addresses[address_lower]
        entity_name = entity_info["name"]
        entity_type = entity_info["type"]
    
    # 태그 생성
    tags = []
    if entity_type == "DEX":
        tags.extend(["DeFi Protocol", "Exchange", "Decentralized"])
    elif entity_type == "Exchange":
        tags.extend(["Exchange", "CEX"])
    
    # Risk tags도 추가
    if graph_data.get("risk_tags"):
        tags.extend(graph_data.get("risk_tags", []))
    
    return {
        "total_received": round(total_received, 2),
        "total_sent": round(total_sent, 2),
        "balance": round(balance, 2),
        "incoming_count": incoming_count,
        "outgoing_count": outgoing_count,
        "total_transactions": len(transactions),
        "first_usage": first_usage,
        "last_usage": last_usage,
        "entity_name": entity_name,
        "entity_type": entity_type,
        "tags": list(set(tags)),  # 중복 제거
        "graph_stats": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "hop1_count": hop1_count,
            "outgoing_relationships": outgoing_count,
            "incoming_relationships": incoming_count,
            "cluster_addresses": hop1_count
        }
    }


def _load_transactions_from_legacy(address: str, chain: str) -> List[Dict[str, Any]]:
    """레거시 데이터에서 거래 데이터 로드"""
    try:
        # 레거시 거래 데이터 경로
        legacy_tx_dir = project_root / "legacy" / "data" / "transactions" / chain
        tx_file = legacy_tx_dir / f"{address}.csv"
        
        if not tx_file.exists():
            return []
        
        # CSV 파일 읽기
        df = pd.read_csv(tx_file)
        
        # SDN/Mixer/Bridge 리스트 로드 (한 번만)
        list_loader = ListLoader()
        sdn_list = list_loader.get_sdn_list()
        mixer_list = list_loader.get_mixer_list()
        bridge_list = list_loader.get_bridge_list()
        
        # 거래 데이터 변환
        # 레거시 데이터는 컨트랙트 주소와 관련된 모든 거래를 포함할 수 있으므로
        # 필터링 없이 모든 거래를 포함 (그래프 구축 시 메인 주소 중심으로 연결)
        transactions = []
        for _, row in df.iterrows():
            from_addr = str(row.get("from", "")).lower()
            to_addr = str(row.get("to", "")).lower()
            
            # 빈 주소나 0x0 주소만 제외
            if not from_addr or not to_addr:
                continue
            if from_addr == "0x0000000000000000000000000000000000000000":
                continue
            if from_addr == "0x0" or to_addr == "0x0":
                continue
            
            tx = {
                "tx_hash": str(row.get("transaction_hash", "")),
                "from": str(row.get("from", "")),
                "to": str(row.get("to", "")),
                "timestamp": int(row.get("timestamp", 0)) if pd.notna(row.get("timestamp")) else 0,
                "usd_value": 0.0,  # USD 변환은 나중에 필요시
                "value": int(row.get("value", 0)) if pd.notna(row.get("value")) else 0,
                "chain": chain,
                "block_height": int(row.get("block_number", 0)) if pd.notna(row.get("block_number")) else 0,
                "is_sanctioned": (from_addr in sdn_list or to_addr in sdn_list),
                "is_mixer": (from_addr in mixer_list or to_addr in mixer_list),
                "is_bridge": (from_addr in bridge_list or to_addr in bridge_list),
            }
            transactions.append(tx)
        
        print(f"✅ 레거시 데이터에서 {len(transactions)}개 거래 로드: {address}")
        return transactions
        
    except Exception as e:
        print(f"⚠️  레거시 데이터 로드 실패: {e}")
        return []


def _build_3hop_graph_data(
    main_address: str,
    transactions: List[Dict[str, Any]],
    fired_rules: List[Dict[str, Any]],
    risk_tags: List[str],
    max_hops: int = 3,
    chain: str = "ethereum",
    etherscan_api_key: str = None,
    use_etherscan: bool = False
) -> Dict[str, Any]:
    """3-hop 그래프 데이터 생성 (인터랙티브 확장 가능)"""
    main_address_lower = main_address.lower()
    
    # NetworkX 그래프 구축
    graph = nx.DiGraph()
    node_info = {}  # 노드 메타데이터 저장
    
    # 1-hop: 모든 거래를 그래프에 추가하고 메인 주소를 중심으로 연결
    hop1_addresses = set()
    print(f"🔍 그래프 구축 시작: {len(transactions)}개 거래 처리 중...")
    
    # 거래를 시간 순서로 정렬 (타임라인 기반 레이아웃을 위해)
    sorted_transactions = sorted(transactions, key=lambda x: x.get("timestamp", 0))
    
    # 먼저 모든 거래를 그래프에 추가
    all_addresses = set()
    for tx in sorted_transactions:
        from_addr = str(tx.get("from", "")).lower().strip()
        to_addr = str(tx.get("to", "")).lower().strip()
        
        # 빈 주소나 0x0 주소 제외
        if not from_addr or not to_addr or from_addr == "0x0" or to_addr == "0x0":
            continue
        if from_addr == "0x0000000000000000000000000000000000000000":
            continue
        
        all_addresses.add(from_addr)
        all_addresses.add(to_addr)
        
        # value 계산 (USD 우선, 없으면 Wei를 ETH로 변환)
        value = tx.get("usd_value", 0)
        if value == 0:
            wei_value = tx.get("value", 0)
            if isinstance(wei_value, (int, float)) and wei_value > 0:
                value = wei_value / 1e18  # Wei -> ETH
        
        # 모든 거래를 그래프에 추가
        if graph.has_edge(from_addr, to_addr):
            graph[from_addr][to_addr]["weight"] += value
            graph[from_addr][to_addr]["tx_count"] += 1
        else:
            graph.add_edge(from_addr, to_addr, weight=value, hop=0, tx_count=1)  # 일단 hop=0으로 설정
    
    # 메인 주소가 그래프에 없으면 추가
    if main_address_lower not in graph:
        graph.add_node(main_address_lower)
    
    # 메인 주소와 직접 연결된 주소 찾기 (1-hop)
    # 레거시 데이터의 경우, 메인 주소가 직접 거래에 없을 수 있으므로
    # 가장 많이 연결된 주소들을 1-hop으로 연결
    if main_address_lower in all_addresses:
        # 메인 주소가 거래에 직접 포함된 경우
        for tx in transactions:
            from_addr = str(tx.get("from", "")).lower().strip()
            to_addr = str(tx.get("to", "")).lower().strip()
            
            if from_addr == main_address_lower and to_addr != main_address_lower:
                hop1_addresses.add(to_addr)
                if not graph.has_edge(main_address_lower, to_addr):
                    graph.add_edge(main_address_lower, to_addr, weight=0, hop=1, tx_count=0)
                graph[main_address_lower][to_addr]["hop"] = 1
            elif to_addr == main_address_lower and from_addr != main_address_lower:
                hop1_addresses.add(from_addr)
                if not graph.has_edge(from_addr, main_address_lower):
                    graph.add_edge(from_addr, main_address_lower, weight=0, hop=1, tx_count=0)
                graph[from_addr][main_address_lower]["hop"] = 1
    else:
        # 메인 주소가 거래에 직접 포함되지 않은 경우
        # 가장 많이 연결된 주소들을 1-hop으로 연결 (최대 20개)
        address_connections = {}
        for addr in all_addresses:
            if addr == main_address_lower:
                continue
            in_degree = graph.in_degree(addr)
            out_degree = graph.out_degree(addr)
            address_connections[addr] = in_degree + out_degree
        
        # 연결이 많은 순으로 정렬하여 1-hop으로 추가
        sorted_addresses = sorted(address_connections.items(), key=lambda x: x[1], reverse=True)
        for addr, _ in sorted_addresses[:20]:  # 최대 20개
            hop1_addresses.add(addr)
            if not graph.has_edge(main_address_lower, addr):
                graph.add_edge(main_address_lower, addr, weight=0, hop=1, tx_count=0)
            graph[main_address_lower][addr]["hop"] = 1
    
    # 노드 정보 업데이트
    for addr in hop1_addresses:
        if addr not in node_info:
            node_info[addr] = {"hop": 1, "type": "address", "total_value": 0, "tx_count": 0}
    
    # 그래프의 모든 노드에 대해 hop 정보 업데이트
    for node_id in graph.nodes():
        if node_id == main_address_lower:
            continue
        if node_id not in hop1_addresses:
            # 2-hop 이상으로 설정 (나중에 실제 hop 계산)
            if node_id not in node_info:
                node_info[node_id] = {"hop": 2, "type": "address", "total_value": 0, "tx_count": 0}
    
    print(f"✅ 1-hop 그래프 구축 완료: {len(hop1_addresses)}개 1-hop 주소, {len(graph.nodes())}개 노드, {len(graph.edges())}개 엣지")
    
    # 메인 주소 정보
    node_info[main_address_lower] = {
        "hop": 0,
        "type": "main_address",
        "total_value": 0,
        "tx_count": len(transactions)
    }
    
    # 2-hop, 3-hop 확장 (Etherscan API 사용)
    if max_hops > 1 and use_etherscan and etherscan_api_key:
        try:
            collector = RealDataCollector(api_key=etherscan_api_key, chain=chain)
            
            # 2-hop: 1-hop 주소들의 거래 수집
            hop2_addresses = set()
            for hop1_addr in list(hop1_addresses)[:10]:  # 최대 10개만 (Rate limit 고려)
                try:
                    hop1_txs = collector.collect_address_transactions(
                        address=hop1_addr,
                        max_transactions=20  # 주소당 최대 20개
                    )
                    
                    for tx in hop1_txs:
                        from_addr = tx.get("from", "").lower()
                        to_addr = tx.get("to", "").lower()
                        value = tx.get("amount_usd", tx.get("value_eth", 0))
                        
                        if from_addr == hop1_addr:
                            if to_addr not in hop1_addresses and to_addr != main_address_lower:
                                hop2_addresses.add(to_addr)
                                graph.add_edge(hop1_addr, to_addr, weight=value, hop=2, tx_count=1)
                                if to_addr not in node_info:
                                    node_info[to_addr] = {"hop": 2, "type": "address", "total_value": value, "tx_count": 1}
                                else:
                                    node_info[to_addr]["total_value"] += value
                                    node_info[to_addr]["tx_count"] += 1
                        elif to_addr == hop1_addr:
                            if from_addr not in hop1_addresses and from_addr != main_address_lower:
                                hop2_addresses.add(from_addr)
                                graph.add_edge(from_addr, hop1_addr, weight=value, hop=2, tx_count=1)
                                if from_addr not in node_info:
                                    node_info[from_addr] = {"hop": 2, "type": "address", "total_value": value, "tx_count": 1}
                                else:
                                    node_info[from_addr]["total_value"] += value
                                    node_info[from_addr]["tx_count"] += 1
                    
                    time.sleep(0.2)  # Rate limit
                except Exception as e:
                    print(f"⚠️  2-hop 수집 실패 ({hop1_addr}): {e}")
                    continue
            
            # 3-hop: 2-hop 주소들의 거래 수집 (선택적, 더 제한적)
            if max_hops >= 3:
                for hop2_addr in list(hop2_addresses)[:5]:  # 최대 5개만
                    try:
                        hop2_txs = collector.collect_address_transactions(
                            address=hop2_addr,
                            max_transactions=10  # 주소당 최대 10개
                        )
                        
                        for tx in hop2_txs:
                            from_addr = tx.get("from", "").lower()
                            to_addr = tx.get("to", "").lower()
                            value = tx.get("amount_usd", tx.get("value_eth", 0))
                            
                            if from_addr == hop2_addr:
                                if to_addr not in hop1_addresses and to_addr not in hop2_addresses and to_addr != main_address_lower:
                                    graph.add_edge(hop2_addr, to_addr, weight=value, hop=3, tx_count=1)
                                    if to_addr not in node_info:
                                        node_info[to_addr] = {"hop": 3, "type": "address", "total_value": value, "tx_count": 1}
                            elif to_addr == hop2_addr:
                                if from_addr not in hop1_addresses and from_addr not in hop2_addresses and from_addr != main_address_lower:
                                    graph.add_edge(from_addr, hop2_addr, weight=value, hop=3, tx_count=1)
                                    if from_addr not in node_info:
                                        node_info[from_addr] = {"hop": 3, "type": "address", "total_value": value, "tx_count": 1}
                        
                        time.sleep(0.2)  # Rate limit
                    except Exception as e:
                        print(f"⚠️  3-hop 수집 실패 ({hop2_addr}): {e}")
                        continue
        except Exception as e:
            print(f"⚠️  Etherscan 3-hop 수집 실패: {e}")
    
    # vis-network용 노드와 엣지 생성
    nodes = []
    edges = []
    
    # 메인 주소의 엔티티 정보 확인
    main_entity_name = None
    main_entity_type = "Unknown"
    known_addresses = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {"name": "Uniswap", "type": "DEX", "icon": "🦄"},
        "0xe592427a0aece92de3edee1f18e0157c05861564": {"name": "Uniswap V3", "type": "DEX", "icon": "🦄"},
        "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": {"name": "Binance", "type": "Exchange", "icon": "🏦"},
    }
    if main_address_lower in known_addresses:
        main_entity_info = known_addresses[main_address_lower]
        main_entity_name = main_entity_info["name"]
        main_entity_type = main_entity_info["type"]
    
    # 메인 주소 노드 (타임라인의 끝에 배치)
    main_label = main_address[:10] + "..."
    if main_entity_name:
        main_label = f"{main_entity_info.get('icon', '📄')} {main_entity_name}"
    
    nodes.append({
        "id": main_address_lower,
        "label": main_label,
        "title": f"{main_address}\nHop: 0 (Main)\n{main_entity_name or 'Address'}",
        "type": "main_address",
        "hop": 0,
        "address": main_address,
        "entity_name": main_entity_name,
        "entity_type": main_entity_type,
        "level": 999  # hierarchical 레이아웃에서 가장 오른쪽에 배치
    })
    
    # 그래프의 모든 노드 추가 (가독성을 위해 제한적으로)
    # 1-hop 주소는 최대 15개만 표시, 나머지는 최대 10개만 표시
    hop1_nodes = []
    other_nodes = []
    
    # 1-hop 주소를 연결 수 기준으로 정렬 (중요한 것만 표시)
    hop1_sorted = []
    for addr in hop1_addresses:
        in_degree = graph.in_degree(addr) if addr in graph else 0
        out_degree = graph.out_degree(addr) if addr in graph else 0
        total_degree = in_degree + out_degree
        hop1_sorted.append((addr, total_degree))
    hop1_sorted.sort(key=lambda x: x[1], reverse=True)
    
    # 1-hop 노드 추가 (최대 30개, 시간 순서로 레벨 배치)
    # 각 노드의 첫 거래 시간을 기준으로 레벨 결정
    node_first_tx_time = {}  # 노드별 첫 거래 시간
    for tx in sorted_transactions:
        from_addr = str(tx.get("from", "")).lower().strip()
        to_addr = str(tx.get("to", "")).lower().strip()
        timestamp = tx.get("timestamp", 0)
        
        if from_addr and from_addr != main_address_lower:
            if from_addr not in node_first_tx_time:
                node_first_tx_time[from_addr] = timestamp
            else:
                node_first_tx_time[from_addr] = min(node_first_tx_time[from_addr], timestamp)
        
        if to_addr and to_addr != main_address_lower:
            if to_addr not in node_first_tx_time:
                node_first_tx_time[to_addr] = timestamp
            else:
                node_first_tx_time[to_addr] = min(node_first_tx_time[to_addr], timestamp)
    
    # 시간을 레벨로 변환 (최대 10개 레벨)
    if node_first_tx_time:
        min_time = min(node_first_tx_time.values())
        max_time = max(node_first_tx_time.values())
        time_range = max_time - min_time if max_time > min_time else 1
    
    for addr, _ in hop1_sorted[:30]:
        if addr == main_address_lower:
            continue
        
        info = node_info.get(addr, {})
        total_value = info.get("total_value", 0)
        tx_count = info.get("tx_count", 0)
        
        # 시간 기반 레벨 계산 (0-9 사이)
        level = 0
        if addr in node_first_tx_time and time_range > 0:
            normalized_time = (node_first_tx_time[addr] - min_time) / time_range
            level = int(normalized_time * 9)  # 0-9 레벨
        
        # 노드의 엔티티 정보 확인
        node_entity_name = None
        node_entity_type = "Unknown"
        if addr in known_addresses:
            node_entity_info = known_addresses[addr]
            node_entity_name = node_entity_info["name"]
            node_entity_type = node_entity_info["type"]
        
        # 라벨 생성 (엔티티가 있으면 아이콘과 이름 표시)
        node_label = addr[:8] + ".."
        if node_entity_name:
            node_label = f"{known_addresses[addr].get('icon', '📄')} {node_entity_name[:8]}"
        
        node_data = {
            "id": addr,
            "label": node_label,
            "title": f"{addr}\nHop: 1\nConnections: {graph.in_degree(addr) + graph.out_degree(addr)}\n{node_entity_name or 'Address'}",
            "type": "address",
            "hop": 1,
            "address": addr,
            "size": 20,  # 크기 통일
            "expanded": False,
            "level": level,  # hierarchical 레이아웃용 레벨
            "entity_name": node_entity_name,
            "entity_type": node_entity_type
        }
        hop1_nodes.append(node_data)
    
    # 나머지 노드 중에서도 연결이 많은 것만 선택 (최대 10개)
    other_sorted = []
    for node_id in graph.nodes():
        if node_id == main_address_lower or node_id in hop1_addresses:
            continue
        
        in_degree = graph.in_degree(node_id) if node_id in graph else 0
        out_degree = graph.out_degree(node_id) if node_id in graph else 0
        total_degree = in_degree + out_degree
        if total_degree > 0:
            other_sorted.append((node_id, total_degree))
    
    other_sorted.sort(key=lambda x: x[1], reverse=True)
    
    for node_id, _ in other_sorted[:10]:
        info = node_info.get(node_id, {})
        hop = info.get("hop", 2)
        
        node_data = {
            "id": node_id,
            "label": node_id[:8] + "..",  # 라벨 짧게
            "title": f"{node_id}\nHop: {hop}",
            "type": "address",
            "hop": hop,
            "address": node_id,
            "size": 15,  # 작게
            "expanded": False
        }
        other_nodes.append(node_data)
    
    # 노드 추가 (1-hop만 기본 표시, 나머지는 확장 시에만)
    # 1-hop 노드는 최대 30개만 표시 (연결이 많은 순으로)
    if len(hop1_nodes) > 30:
        # 1-hop 노드를 연결 수 기준으로 정렬
        hop1_with_degree = []
        for node_data in hop1_nodes:
            node_id = node_data["id"]
            degree = graph.degree(node_id) if node_id in graph else 0
            hop1_with_degree.append((degree, node_data))
        hop1_with_degree.sort(reverse=True, key=lambda x: x[0])
        hop1_nodes = [node_data for _, node_data in hop1_with_degree[:30]]
    
    # 기본적으로 1-hop만 표시
    nodes.extend(hop1_nodes)
    # other_nodes는 확장 시에만 추가 (여기서는 추가 안 함)
    
    # 메인 주소와 1-hop 노드 간 연결 확인 및 추가
    visible_node_ids = {n["id"] for n in nodes}
    
    # 메인 주소가 다른 노드와 연결되지 않았을 경우, 1-hop 노드와 연결 생성
    main_has_edges = any(
        (main_address_lower == from_addr or main_address_lower == to_addr)
        for from_addr, to_addr in graph.edges()
    )
    
    if not main_has_edges and hop1_nodes:
        # 메인 주소와 1-hop 노드 간 가상 엣지 추가 (시각화용)
        for hop1_node in hop1_nodes[:10]:  # 최대 10개만
            hop1_addr = hop1_node["id"]
            # 그래프에 실제 연결이 있는지 확인
            if graph.has_edge(main_address_lower, hop1_addr) or graph.has_edge(hop1_addr, main_address_lower):
                continue  # 이미 연결이 있으면 스킵
            
            # 가상 엣지 추가 (시각화를 위해)
            graph.add_edge(main_address_lower, hop1_addr, weight=0, hop=1, tx_count=0)
    
    # 표시되는 노드만 엣지 추가 (가독성 향상)
    visible_node_ids = {n["id"] for n in nodes}
    
    for from_addr, to_addr, data in graph.edges(data=True):
        # 양쪽 노드가 모두 표시되는 경우만 엣지 추가
        if from_addr not in visible_node_ids or to_addr not in visible_node_ids:
            continue
        
        weight = data.get("weight", 0)
        hop = data.get("hop", 1)
        tx_count = data.get("tx_count", 1)
        
        # 엣지 라벨 간소화 (너무 많은 정보 표시 안 함)
        # 큰 값만 표시하고 나머지는 생략
        if weight > 1000000:
            label = f"{weight/1000000:.1f}M"
        elif weight > 10000:
            label = f"{weight/1000:.0f}K"
        elif weight > 1000:
            label = f"{weight/1000:.1f}K"
        else:
            label = ""  # 작은 값은 라벨 생략
        
        # 엣지 두께는 가중치에 따라 조정 (1-5 사이)
        width = 1
        if weight > 0:
            if weight > 1000000:
                width = 5
            elif weight > 100000:
                width = 4
            elif weight > 10000:
                width = 3
            elif weight > 1000:
                width = 2
            else:
                width = 1
        
        # 엣지에 연결된 거래 정보 찾기 (첫 번째 거래만 표시)
        edge_transactions = []
        for tx in sorted_transactions:
            tx_from = str(tx.get("from", "")).lower().strip()
            tx_to = str(tx.get("to", "")).lower().strip()
            if tx_from == from_addr and tx_to == to_addr:
                edge_transactions.append(tx)
                if len(edge_transactions) >= 5:  # 최대 5개만
                    break
        
        edges.append({
            "id": f"{from_addr}_{to_addr}",
            "from": from_addr,
            "to": to_addr,
            "label": label,
            "type": "transaction",
            "hop": hop,
            "weight": weight,
            "tx_count": tx_count,
            "width": width,
            "transactions": edge_transactions  # 거래 정보 추가
        })
    
    # 룰 노드 추가
    for rule in fired_rules:
        rule_id = rule.get("rule_id", "")
        if rule_id:
            nodes.append({
                "id": f"rule_{rule_id}",
                "label": rule_id,
                "title": f"Rule: {rule_id}\nScore: {rule.get('score', 0)}",
                "type": "rule",
                "hop": 0,
                "score": rule.get("score", 0)
            })
            
            edges.append({
                "id": f"{main_address_lower}_rule_{rule_id}",
                "from": main_address_lower,
                "to": f"rule_{rule_id}",
                "label": f"{rule.get('score', 0)}점",
                "type": "rule_connection",
                "dashes": True
            })
    
    # 태그 노드 추가
    for tag in risk_tags:
        nodes.append({
            "id": f"tag_{tag}",
            "label": tag,
            "title": f"Risk Tag: {tag}",
            "type": "tag",
            "hop": 0
        })
        
        edges.append({
            "id": f"{main_address_lower}_tag_{tag}",
            "from": main_address_lower,
            "to": f"tag_{tag}",
            "type": "tag_connection",
            "dashes": [5, 5]
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "graph_stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "max_hops": max_hops,
            "hop1_count": len(hop1_addresses),
            "hop2_count": len(hop2_addresses) if 'hop2_addresses' in locals() else 0,
            "hop3_count": sum(1 for n in nodes if n.get("hop") == 3)
        }
    }

# Stage 1 + Stage 2 스코어러 초기화
stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
stage2_scorer = None  # 필요시 로드


def load_stage2_scorer():
    """Stage 2 스코어러 로드 (지연 로딩)"""
    global stage2_scorer
    if stage2_scorer is None:
        try:
            # 최적화된 모델 우선 사용, 없으면 기존 모델 사용
            model_path = project_root / "models" / "improved_stage2_model.pkl"
            if not model_path.exists():
                model_path = project_root / "models" / "stage2_scorer_gradient_boosting.pkl"
            if not model_path.exists():
                model_path = project_root / "data" / "dataset" / "stage2_scorer_gradient_boosting.pkl"
            
            if model_path.exists():
                stage2_scorer = Stage2Scorer()
                stage2_scorer.load_model(model_path)
                print(f"✅ Stage 2 모델 로드 완료: {model_path.name}")
            else:
                print("⚠️  Stage 2 모델 파일을 찾을 수 없습니다. Stage 1만 사용합니다.")
        except Exception as e:
            print(f"⚠️  Stage 2 모델 로드 실패: {e}. Stage 1만 사용합니다.")
    return stage2_scorer


@demo_analysis_bp.route("/address/demo", methods=["POST"])
def analyze_address_demo():
    """
    데모용 주소 분석 (Stage 1 + Stage 2)
    
    ---
    tags:
      - Demo
    summary: 주소 리스크 분석 (데모용)
    description: Stage 1 (Rule-based + Graph) + Stage 2 (AI) 통합 분석
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - address
            - chain
          properties:
            address:
              type: string
              description: 분석할 주소
              example: "0x3e66b66fd1d0b02fda6c811da9e0547970db2f21"
            chain:
              type: string
              description: 블록체인
              example: "ethereum"
            transactions:
              type: array
              description: 거래 데이터 (선택사항)
              items:
                type: object
            analysis_type:
              type: string
              description: 분석 타입 (basic/advanced)
              example: "advanced"
    responses:
      200:
        description: 분석 성공
        schema:
          type: object
          properties:
            target_address:
              type: string
            risk_score:
              type: number
            risk_level:
              type: string
            rule_score:
              type: number
            graph_score:
              type: number
            stage1_score:
              type: number
            stage2_score:
              type: number
            risk_tags:
              type: array
              items:
                type: string
            fired_rules:
              type: array
              items:
                type: object
            explanation:
              type: string
      400:
        description: 잘못된 요청
      500:
        description: 서버 오류
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        address = data.get("address") or data.get("target_address")
        chain = data.get("chain", "ethereum")
        transactions = data.get("transactions", [])
        analysis_type = data.get("analysis_type", "advanced")
        use_etherscan = data.get("use_etherscan", False)  # Etherscan API 사용 여부
        etherscan_api_key = data.get("etherscan_api_key") or "91FZVKNIX7GYPESECU5PHPZIMKD72REX43"  # 사용자 제공 API 키 또는 기본값
        max_hops = data.get("max_hops", 3)  # 기본 3-hop
        
        if not address:
            return jsonify({"error": "Missing required field: address"}), 400
        
        # 거래 데이터가 없으면 자동으로 수집
        if not transactions:
            # 1. 레거시 데이터에서 먼저 시도
            transactions = _load_transactions_from_legacy(address, chain)
            
            # 2. 레거시 데이터가 없고 Etherscan 사용이 활성화되어 있으면 API 호출
            if not transactions and use_etherscan:
                try:
                    etherscan_client = EtherscanClient(api_key=etherscan_api_key, chain=chain)
                    # 최근 100개 거래만 가져오기 (Rate limit 고려)
                    raw_txs = etherscan_client.get_transactions(
                        address=address,
                        page=1,
                        offset=100,  # 최대 100개
                        sort="desc"  # 최신순
                    )
                    
                    # Etherscan 응답을 표준 형식으로 변환
                    transactions = []
                    for raw_tx in raw_txs:
                        normalized = etherscan_client.normalize_transaction(raw_tx, chain)
                        
                        # 타임스탬프 변환 (ISO -> Unix timestamp)
                        timestamp_str = normalized.get("timestamp", "")
                        timestamp = 0
                        if timestamp_str:
                            try:
                                from datetime import datetime
                                if timestamp_str.endswith("Z"):
                                    timestamp_str = timestamp_str[:-1] + "+00:00"
                                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                timestamp = int(dt.timestamp())
                            except:
                                pass
                        
                        # SDN/Mixer/Bridge 리스트 확인
                        list_loader = ListLoader()
                        sdn_list = list_loader.get_sdn_list()
                        mixer_list = list_loader.get_mixer_list()
                        bridge_list = list_loader.get_bridge_list()
                        
                        from_addr = normalized.get("from", "").lower()
                        to_addr = normalized.get("to", "").lower()
                        
                        # 표준 형식으로 변환
                        tx = {
                            "tx_hash": normalized.get("tx_hash", ""),
                            "from": normalized.get("from", ""),
                            "to": normalized.get("to", ""),
                            "timestamp": timestamp,
                            "usd_value": normalized.get("amount_usd", 0.0),
                            "value": normalized.get("value_wei", 0),
                            "chain": chain,
                            "block_height": normalized.get("block_height", 0),
                            "is_sanctioned": (from_addr in sdn_list or to_addr in sdn_list),
                            "is_mixer": (from_addr in mixer_list or to_addr in mixer_list),
                            "is_bridge": (from_addr in bridge_list or to_addr in bridge_list),
                        }
                        transactions.append(tx)
                    
                    print(f"✅ Etherscan에서 {len(transactions)}개 거래 수집: {address}")
                except Exception as e:
                    print(f"⚠️  Etherscan API 호출 실패: {e}")
                    # Etherscan 실패해도 레거시 데이터가 있으면 계속 진행
                    if not transactions:
                        return jsonify({
                            "error": f"거래 데이터를 찾을 수 없습니다. 레거시 데이터와 Etherscan API 모두 실패했습니다.",
                            "details": str(e)
                        }), 404
            elif not transactions:
                # 거래 데이터가 없으면 경고 메시지와 함께 기본 분석 진행
                print(f"⚠️  거래 데이터 없음: {address} (레거시 데이터와 Etherscan 모두 사용 안 함)")
        
        # Stage 1 분석
        # 거래 데이터를 Stage 1 형식으로 변환
        tx_data_list = []
        ml_features_list = []
        tx_context_list = []
        
        for tx in transactions:
            # Stage 1용 거래 데이터
            tx_data = {
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "usd_value": tx.get("usd_value", tx.get("amount_usd", 0)),
                "timestamp": tx.get("timestamp", 0),
                "tx_hash": tx.get("tx_hash", ""),
                "chain": chain,
                "is_sanctioned": tx.get("is_sanctioned", False),
                "is_mixer": tx.get("is_mixer", False),
                "is_bridge": tx.get("is_bridge", False),
            }
            tx_data_list.append(tx_data)
            
            # ML features (간단한 버전)
            ml_features = {
                "fan_in_count": 0,
                "fan_out_count": 0,
                "pattern_score": 0.0,
                "ppr_score": 0.0,
                "sdn_ppr": 0.0,
                "mixer_ppr": 0.0,
                "n_theta": 0.0,
                "n_omega": 0.0,
            }
            ml_features_list.append(ml_features)
            
            # Transaction context
            tx_context = {
                "num_transactions": len(transactions),
                "graph_nodes": 0,
                "graph_edges": 0,
                "is_sanctioned": tx.get("is_sanctioned", False),
                "is_mixer": tx.get("is_mixer", False),
            }
            tx_context_list.append(tx_context)
        
        # Stage 1 점수 계산 (첫 번째 거래 기준 또는 전체 평균)
        if tx_data_list:
            stage1_results = []
            for tx_data, ml_features, tx_context in zip(tx_data_list, ml_features_list, tx_context_list):
                result = stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
                stage1_results.append(result)
            
            # 평균 점수 계산
            rule_score = sum(r["rule_score"] for r in stage1_results) / len(stage1_results)
            graph_score = sum(r["graph_score"] for r in stage1_results) / len(stage1_results)
            stage1_score = sum(r["risk_score"] for r in stage1_results) / len(stage1_results)
            
            # 발동된 룰 수집
            all_fired_rules = []
            for result in stage1_results:
                all_fired_rules.extend(result.get("fired_rules", []))
            
            # 중복 제거
            unique_rules = {}
            for rule in all_fired_rules:
                rule_id = rule.get("rule_id", "")
                if rule_id and rule_id not in unique_rules:
                    unique_rules[rule_id] = rule
            
            fired_rules = list(unique_rules.values())
        else:
            # 거래 데이터가 없을 때
            rule_score = 0.0
            graph_score = 0.0
            stage1_score = 0.0
            fired_rules = []
        
        # Stage 2 점수 계산 (선택적)
        stage2_score = None
        if tx_data_list and stage1_results:
            stage2_scorer_obj = load_stage2_scorer()
            if stage2_scorer_obj:
                try:
                    # Stage 2용 feature 추출
                    features = stage2_scorer_obj._extract_features(
                        stage1_results[0],  # 첫 번째 결과 사용
                        ml_features_list[0] if ml_features_list else {},
                        tx_context_list[0] if tx_context_list else {}
                    )
                    
                    # Stage 2 예측
                    ml_proba = stage2_scorer_obj.model.predict_proba(
                        stage2_scorer_obj.scaler.transform(features.reshape(1, -1))
                    )[0]
                    stage2_score = ml_proba[1] * 100.0  # Fraud 확률을 점수로 변환
                    
                    # Stage 1 + Stage 2 결합 (가중치: 0.6, 0.4)
                    final_score = 0.6 * stage1_score + 0.4 * stage2_score
                except Exception as e:
                    print(f"⚠️  Stage 2 예측 실패: {e}")
                    final_score = stage1_score
            else:
                final_score = stage1_score
        else:
            final_score = stage1_score
        
        # Risk Level 결정
        if final_score >= 80:
            risk_level = "critical"
        elif final_score >= 60:
            risk_level = "high"
        elif final_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Risk Tags 생성
        risk_tags = []
        if any(r.get("rule_id", "").startswith("E-101") for r in fired_rules):
            risk_tags.append("mixer_inflow")
        if any(r.get("rule_id", "").startswith("C-001") for r in fired_rules):
            risk_tags.append("sanction_exposure")
        if any(r.get("rule_id", "").startswith("C-003") for r in fired_rules):
            risk_tags.append("high_value_transfer")
        if any(r.get("rule_id", "").startswith("B-501") for r in fired_rules):
            risk_tags.append("high_value_buckets")
        
        # Explanation 생성
        if fired_rules:
            top_rule = max(fired_rules, key=lambda r: r.get("score", 0))
            explanation = f"{top_rule.get('rule_id', 'Unknown')} 룰이 발동되어 {risk_level} 리스크로 분류됨."
        else:
            explanation = "발동된 룰이 없어 낮은 리스크로 분류됨."
        
        # 3-hop 그래프 구축 및 그래프 데이터 생성
        graph_data = _build_3hop_graph_data(
            address, transactions, fired_rules, risk_tags, max_hops=max_hops, 
            chain=chain, etherscan_api_key=etherscan_api_key, use_etherscan=use_etherscan
        )
        
        # IKNA 스타일 상세 정보 계산
        address_stats = _calculate_address_stats(address, transactions, graph_data)
        
        return jsonify({
            "target_address": address,
            "risk_score": round(final_score, 2),
            "risk_level": risk_level,
            "rule_score": round(rule_score, 2),
            "graph_score": round(graph_score, 2),
            "stage1_score": round(stage1_score, 2),
            "stage2_score": round(stage2_score, 2) if stage2_score is not None else None,
            "risk_tags": risk_tags,
            "fired_rules": [
                {
                    "rule_id": r.get("rule_id", ""),
                    "score": r.get("score", 0)
                }
                for r in fired_rules
            ],
            "explanation": explanation,
            "graph": graph_data,  # 그래프 데이터 추가
            "transactions": transactions,  # 거래 목록 추가 (오른쪽 패널용)
            "address_stats": address_stats  # IKNA 스타일 상세 정보
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"Analysis failed: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

