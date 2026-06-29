import { useOutletContext } from "react-router";
import * as S from "./style";

import RektCard from "@/components/case/RektsCard";
import { useEffect, useState } from "react";
import { fetchRekts } from "@/api/fetchReckts";
import { RektItem } from "@/types/rekt";
import { Reckts } from "@/data/dummyRekts";


type LayoutContext = {
  title: string;
  intro: string;
};

export default function CasePage() {
  const { title, intro } = useOutletContext<LayoutContext>();
  const [data, setData] = useState<RektItem[]>([]);  

useEffect(() => {
  fetchRekts({ pageNumber: 1, pageSize: 20 })
    .then((res) => {
      console.log("🔥 fetchRekts response:", res);

      if (!res) {
        console.log("❌ res is undefined");
        return;
      }

      if (res.error) {
        console.log("❌ API Error:", res.error);
      }

      if (!res.data) {
        console.log("❌ res.data is undefined:", res);
      } else {
        console.log("✅ data length:", res.data.length);
        setData(res.data);
      }
    })
    .catch((err) => {
      console.log("🔥 CATCH ERROR", err);
    });
}, []);


  return (
    <S.Root>
      <S.HeaderSection>
        <S.Title>{title}</S.Title>
        <S.Intro>{intro}</S.Intro>
      </S.HeaderSection>

      {/* Rekts 리스트 섹션 */}
      <S.ListSection>
        {Reckts.map((item) => (
          <RektCard key={item.id} item={item} />
        ))}
      </S.ListSection>
    </S.Root>
  );
}
