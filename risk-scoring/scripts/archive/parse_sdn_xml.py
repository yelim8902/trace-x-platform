#!/usr/bin/env python3
"""
SDN XML 파일 파싱 및 이더리움 주소 추출
"""
import xml.etree.ElementTree as ET
import re
from pathlib import Path
import json
from collections import defaultdict

def parse_sdn_xml(xml_path: str, output_path: str = None):
    """
    SDN XML 파일에서 이더리움 주소 추출
    
    Args:
        xml_path: SDN XML 파일 경로
        output_path: 출력 JSON 파일 경로 (선택사항)
    """
    file_path = Path(xml_path)
    
    print("=" * 80)
    print("SDN XML 파일 분석")
    print("=" * 80)
    
    print(f"\n📂 파일 정보:")
    print(f"  파일 크기: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # XML 파싱
    print(f"\n🔄 XML 파싱 중...")
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # 네임스페이스
    ns_uri = 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML'
    ns = {'sdn': ns_uri}
    
    # Publication Info
    pub_info = root.find('sdn:publicationInfo', ns)
    if pub_info is not None:
        data_as_of = pub_info.find('sdn:dataAsOf', ns)
        if data_as_of is not None:
            print(f"\n📅 데이터 기준일: {data_as_of.text}")
    
    # 전체 엔티티 개수
    entities = root.findall('sdn:entities/sdn:entity', ns)
    print(f"\n📊 전체 엔티티 개수: {len(entities):,}개")
    
    # 이더리움 주소 추출
    ethereum_addresses = []
    ethereum_pattern = re.compile(r'0x[a-fA-F0-9]{40}')
    
    # 통계
    entity_types = defaultdict(int)
    has_digital_currency = 0
    digital_currency_types = defaultdict(int)
    
    print(f"\n🔄 이더리움 주소 추출 중...")
    for i, entity in enumerate(entities):
        if (i + 1) % 5000 == 0:
            print(f"  처리 중... {i+1:,}/{len(entities):,}개 엔티티, {len(ethereum_addresses)}개 이더리움 주소")
        
        # 엔티티 타입
        profile = entity.find('sdn:profile', ns)
        if profile is not None:
            entity_type = profile.find('sdn:type', ns)
            if entity_type is not None:
                entity_types[entity_type.text] += 1
        
        # DigitalCurrencyAddress 찾기
        digital_currency_addrs = entity.findall('.//sdn:digitalCurrencyAddress', ns)
        if digital_currency_addrs:
            has_digital_currency += 1
            for addr_elem in digital_currency_addrs:
                addr_value = addr_elem.find('sdn:value', ns)
                if addr_value is not None and addr_value.text:
                    addr = addr_value.text.strip().lower()
                    if ethereum_pattern.match(addr):
                        if addr not in ethereum_addresses:
                            ethereum_addresses.append(addr)
                    
                    # 주소 타입 확인
                    addr_type_elem = addr_elem.find('sdn:type', ns)
                    if addr_type_elem is not None:
                        digital_currency_types[addr_type_elem.text] += 1
        
        # 일반 value 태그에서도 찾기 (백업)
        for value_elem in entity.findall('.//sdn:value', ns):
            if value_elem.text:
                text = value_elem.text.strip().lower()
                if ethereum_pattern.match(text):
                    if text not in ethereum_addresses:
                        ethereum_addresses.append(text)
    
    print(f"\n📊 최종 분석 결과:")
    print(f"  전체 엔티티: {len(entities):,}개")
    print(f"  디지털 통화 주소가 있는 엔티티: {has_digital_currency:,}개")
    print(f"  이더리움 주소: {len(ethereum_addresses)}개")
    
    print(f"\n📋 엔티티 타입 분포:")
    for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {entity_type}: {count:,}개")
    
    print(f"\n📋 디지털 통화 타입 분포:")
    for currency_type, count in sorted(digital_currency_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {currency_type}: {count:,}개")
    
    if ethereum_addresses:
        print(f"\n✅ 이더리움 주소 샘플 (최대 20개):")
        for i, addr in enumerate(ethereum_addresses[:20]):
            print(f"  {i+1:2d}. {addr}")
    
    # 저장
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(ethereum_addresses, f, indent=2)
        print(f"\n💾 저장 완료: {output_path}")
        print(f"  파일 크기: {output_file.stat().st_size / 1024:.2f} KB")
    
    return ethereum_addresses


if __name__ == "__main__":
    import sys
    
    xml_path = "SDN_ENHANCED 3.XML"
    output_path = "data/lists/sdn_addresses_from_xml.json"
    
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    
    addresses = parse_sdn_xml(xml_path, output_path)

