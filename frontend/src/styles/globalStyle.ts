import { createGlobalStyle } from "styled-components";

const GlobalStyle = createGlobalStyle`
  @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css");

  * {
    margin: 0;
    padding: 0;

    font-family: 'Pretendard','Noto Sans KR', sans-serif;
    font-style: normal;
    line-height: normal;

    box-sizing: border-box; //padding과 border가 width 안에 포함
  }

  #root {
    height: 100%;
    width: 100%;
    display: flex;
    justify-content: center; 
    align-items: center;   
  }

    :root {
    ${({ theme }) =>
      Object.entries(theme.colors)
        .map(([key, value]) => `--${key}: ${value};`)
        .join("\n")}
  }

  html {
    overflow-x: hidden;
  }

  body {
    margin: 0;
    background-color: #f0f0f0; 
    display: flex;
    justify-content: center; 
    align-items: center;     
    height: 100dvh;  
    width: 100%;
    font-family: 'Mona Sans', 'Noto Sans KR', 'Josefin Sans', sans-serif;
    }

  input {
    border: none;
    padding: 0;
    margin: 0;
    background-color: transparent;
  }

  input:focus {
    outline: none;
  }

  /* ====== Scrollbar Style (for all browsers) ====== */

::-webkit-scrollbar {
  width: 8px;               /* 스크롤바 두께 */
  height: 8px;              /* 가로 스크롤용 */
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #0B1739 0%, #0B1739  100%);
  border-radius: 8px;
  transition: all 0.2s ease;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #4f5fa5 0%, #243872 100%);
}



`;

export default GlobalStyle;
