#!/usr/bin/env python3
"""
OFAC SDN 리스트 업데이트 스크립트

OFAC 공식 XML 파일에서 암호화폐 주소를 추출하여 sdn_addresses.json을 업데이트합니다.

사용법:
    python3 scripts/update_sdn_list.py

OFAC XML 다운로드:
    https://www.treasury.gov/ofac/downloads/sdn.xml
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set, Dict, List
import requests
from datetime import datetime


OFAC_XML_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
SDN_OUTPUT_FILE = Path("data/lists/sdn_addresses.json")
SDN_METADATA_FILE = Path("data/lists/sdn_addresses_metadata.json")


def download_sdn_xml(url: str = OFAC_XML_URL) -> bytes:
    """OFAC SDN XML 파일 다운로드"""
    print(f"📥 OFAC SDN XML 다운로드 중...")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print(f"✅ 다운로드 완료 ({len(response.content)} bytes)")
        return response.content
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        raise


def parse_sdn_xml(xml_content: bytes) -> Dict[str, List[str]]:
    """
    OFAC SDN XML에서 암호화폐 주소 추출
    
    XML 구조:
    <sdnEntry>
        <idList>
            <id>
                <idType>Digital Currency Address</idType>
                <idNumber>0xabc123...</idNumber>
            </id>
        </idList>
    </sdnEntry>
    
    Returns:
        {
            "btc": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", ...],
            "eth": ["0xabc123...", ...],
            "bnb": ["bnb1...", ...],
            "usdt": ["0xdef456...", ...],
            ...
        }
    """
    print("🔍 XML 파싱 중...")
    
    root = ET.fromstring(xml_content)
    
    # 네임스페이스 제거 함수
    def strip_ns(tag: str) -> str:
        """태그에서 네임스페이스 제거"""
        if '}' in tag:
            return tag.split('}')[1]
        return tag
    
    addresses_by_type: Dict[str, Set[str]] = {
        "btc": set(),
        "eth": set(),
        "bnb": set(),
        "usdt": set(),
        "other": set(),
    }
    
    total_entries = 0
    digital_currency_count = 0
    
    # 모든 요소 순회하여 sdnEntry 찾기 (네임스페이스 무시)
    for elem in root.iter():
        if strip_ns(elem.tag) != 'sdnEntry':
            continue
        
        total_entries += 1
        
        # idList 찾기
        id_list = None
        for child in elem:
            if strip_ns(child.tag) == 'idList':
                id_list = child
                break
        
        if id_list is None:
            continue
        
        # 각 id 확인
        for id_elem in id_list:
            if strip_ns(id_elem.tag) != 'id':
                continue
            
            # idType, idNumber 찾기
            id_type_text = None
            id_number_text = None
            
            for sub_elem in id_elem:
                tag_name = strip_ns(sub_elem.tag)
                if tag_name == 'idType':
                    id_type_text = (sub_elem.text or "").strip()
                elif tag_name == 'idNumber':
                    id_number_text = (sub_elem.text or "").strip()
            
            if not id_type_text or not id_number_text:
                continue
            
            # Digital Currency Address 확인
            if "Digital Currency Address" in id_type_text or "Digital Currency" in id_type_text:
                digital_currency_count += 1
                
                # 주소 타입 판별
                addr_lower = id_number_text.lower().strip()
                
                if addr_lower.startswith('1') or addr_lower.startswith('3') or addr_lower.startswith('bc1'):
                    # Bitcoin 주소
                    addresses_by_type["btc"].add(id_number_text.strip())
                elif addr_lower.startswith('0x') and len(addr_lower) == 42:
                    # Ethereum 주소 (ERC-20 포함)
                    # USDT 체크 (idType에 USDT가 포함되어 있으면)
                    if "USDT" in id_type_text.upper():
                        addresses_by_type["usdt"].add(id_number_text.strip())
                    else:
                        addresses_by_type["eth"].add(id_number_text.strip())
                elif addr_lower.startswith('bnb'):
                    # Binance Chain 주소
                    addresses_by_type["bnb"].add(id_number_text.strip())
                else:
                    # 기타
                    addresses_by_type["other"].add(id_number_text.strip())
    
    print(f"📊 파싱 결과:")
    print(f"   총 SDN 엔트리: {total_entries}")
    print(f"   암호화폐 주소: {digital_currency_count}")
    print(f"   - BTC: {len(addresses_by_type['btc'])}")
    print(f"   - ETH: {len(addresses_by_type['eth'])}")
    print(f"   - BNB: {len(addresses_by_type['bnb'])}")
    print(f"   - 기타: {len(addresses_by_type['other'])}")
    
    # 모든 주소 합치기 (중복 제거)
    all_addresses = set()
    for addr_set in addresses_by_type.values():
        all_addresses.update(addr_set)
    
    print(f"   총 고유 주소: {len(all_addresses)}")
    
    return {
        "btc": sorted(list(addresses_by_type["btc"])),
        "eth": sorted(list(addresses_by_type["eth"])),
        "bnb": sorted(list(addresses_by_type["bnb"])),
        "other": sorted(list(addresses_by_type["other"])),
        "all": sorted(list(all_addresses)),  # 모든 주소 통합
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "source": OFAC_XML_URL,
            "total_entries": total_entries,
            "digital_currency_count": digital_currency_count,
            "counts": {
                "btc": len(addresses_by_type["btc"]),
                "eth": len(addresses_by_type["eth"]),
                "bnb": len(addresses_by_type["bnb"]),
                "other": len(addresses_by_type["other"]),
                "all": len(all_addresses),
            }
        }
    }


def save_sdn_list(data: Dict, output_file: Path, metadata_file: Path) -> None:
    """
    SDN 리스트를 JSON 파일로 저장.

    ListLoader._load_json_list()가 파싱 가능한 "평면 리스트" 포맷으로 저장해야 함
    (기존 sdn_addresses.json이 이 포맷이었고, 여기에 dict를 그대로 저장하면
    ListLoader가 못 읽어서 SDN_LIST가 조용히 비어버림 — 실제 라이브 컴플라이언스
    룰 C-001/E-102가 이 파일을 읽으므로 포맷을 반드시 지켜야 함).
    전체 통화별 분류 + 메타데이터는 별도 파일에 참고용으로 저장.
    """
    print(f"💾 SDN 리스트 저장 중...")
    print(f"   파일: {output_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data["all"], f, indent=2, ensure_ascii=False)

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ 저장 완료!")
    print(f"   - BTC: {len(data['btc'])}개")
    print(f"   - ETH: {len(data['eth'])}개")
    print(f"   - BNB: {len(data['bnb'])}개")
    print(f"   - 기타: {len(data['other'])}개")
    print(f"   - 전체: {len(data['all'])}개")


def load_existing_sdn_list(file_path: Path) -> Set[str]:
    """기존 SDN 리스트 로드 (비교용)"""
    if not file_path.exists():
        return set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            elif isinstance(data, dict):
                return set(data.get("all", []))
            return set()
    except Exception:
        return set()


def main():
    """메인 함수"""
    print("=" * 70)
    print("🔄 OFAC SDN 리스트 업데이트")
    print("=" * 70)
    print()
    
    # 기존 리스트 로드
    existing_addresses = load_existing_sdn_list(SDN_OUTPUT_FILE)
    print(f"📋 기존 주소 수: {len(existing_addresses)}")
    print()
    
    try:
        # 1. XML 다운로드
        xml_content = download_sdn_xml()
        print()
        
        # 2. XML 파싱
        sdn_data = parse_sdn_xml(xml_content)
        print()
        
        # 3. 변경사항 확인
        new_addresses = set(sdn_data["all"])
        added = new_addresses - existing_addresses
        removed = existing_addresses - new_addresses
        
        print(f"📊 변경사항:")
        print(f"   추가: {len(added)}개")
        print(f"   삭제: {len(removed)}개")
        if added:
            print(f"   추가된 주소 예시: {list(added)[:5]}")
        print()
        
        # 4. 저장
        save_sdn_list(sdn_data, SDN_OUTPUT_FILE, SDN_METADATA_FILE)
        print()
        
        print("=" * 70)
        print("✅ 업데이트 완료!")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ 오류 발생: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()

