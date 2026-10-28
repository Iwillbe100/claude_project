# 근거 기록 형식 (Evidence Record)

모은 정보 1건은 **파일을 따로 만들지 않고** `output/research_data.json` 안에 한 칸으로 들어갑니다.
세기 쉽게 만들려고 그렇게 정했습니다.

---

## 1. 근거 1건의 모양 (고정)

```json
{
  "text": "다낭 미케 비치는 아침 6시쯤 가면 현지인들이 운동하는 모습을 볼 수 있고 사람이 적어 사진 찍기 좋다.",
  "source_url": "https://example.blog/danang-mykhe",
  "source_name": "여행 블로그 · 다낭 3박 4일 후기"
}
```

| 항목 | 뜻 | 없으면 |
| --- | --- | --- |
| `text` | 정리한 내용. 최소 글자 수는 계약의 `min_chars.evidence_item` | 세어 주지 않음 |
| `source_url` | 어디서 봤는지 | 서로 다른 출처를 셀 수 없음 |
| `source_name` | 사람이 알아볼 이름 | 화면에 링크 이름이 안 나옴 |

> **원문을 통째로 붙여넣지 마세요.** 필요한 사실만 내 말로 정리합니다.
> **같은 내용을 여러 건으로 나눠 넣지도 마세요.** 한 칸 안에 같은 근거가 두 번 있으면 걸립니다.
> 기준선에 맞춰 문장을 끊지 말고, 아는 것을 다 적으세요. 하한은 최소일 뿐 목표가 아닙니다.

---

## 2. 출처는 어디든 괜찮습니다

```text
정부 사이트   O
관광청        O
여행 블로그   O   ← 여행은 원래 여기에 쓸 만한 정보가 많습니다
카페 후기글   O
```

**등급을 따지지 않습니다.** 대신 `다건` 항목은 **서로 다른 출처 2곳 이상**에서 와야 합니다.
한 사람 말만 듣고 페이지를 만들지 않기 위해서입니다.

---

## 3. 어느 칸에 들어가나

```text
output/research_data.json
  country_intro.매력.items[]         국가 소개 근거
  country_intro.환율.items[]         단건 — 1건이면 충족
  cities[].spots[].items[]           관광지 근거
  cities[].itinerary.items[]         일정 근거
```

---

## 4. 이미지는 형식이 다릅니다

```json
{
  "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Hoi%20An%20Ancient%20Town.jpg?width=1024",
  "alt": "밤에 등불이 켜진 호이안 구시가지",
  "source_url": "https://example.com/hoian-guide",
  "verified": {"status": 200, "content_type": "image/jpeg",
               "checked_at": "2026-09-05T15:02:11"}
}
```

`url` · `alt` · `verified` 가 **모두** 있어야 1장으로 셉니다.
`alt`는 사진이 안 열릴 때 대신 보여 줄 글이라 비워 두면 안 됩니다.

**`verified` 는 실제로 열어 봤다는 기록입니다.**

```text
주소를 기억으로 쓰지 않습니다. 조회로 얻고, 열어 보고, 그 결과를 적습니다.

  금지   upload.wikimedia.org/...  (thumb 이든 원본이든 전부 — 조회로 얻은 주소도 검사기가 SHORT)
  권장   https://commons.wikimedia.org/wiki/Special:FilePath/<파일명>?width=1024
```

한 번은 이미지 11장이 **전부 죽어 있는데 검사를 통과**한 적이 있습니다.
주소는 다 있었고, 살아 있는지는 아무도 안 봤기 때문입니다.

> **검사기는 인터넷에 접속하지 않습니다.** 접속해서 확인한 *기록*을 봅니다.
> 확인은 모으는 사람의 일이고, 기록을 남기는 것이 계약입니다.

---

## 5. 누가 판정하는가

| 판정 | 담당 |
| --- | --- |
| 내 취향과 관련이 있는가 | LLM |
| 이 글이 쓸 만한가 | LLM |
| 계약의 최소 글자 수를 넘는가 | 코드 |
| 같은 문장을 복사하지 않았는가 | 코드 |
| 이미지를 실제로 열어 본 기록이 있는가 | 코드 |
| 서로 다른 출처가 몇 곳인가 | 코드 |
| 개수가 목표에 닿았는가 | 코드 |
