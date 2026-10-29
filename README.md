# Frieren Archive — 나의 굿즈 수집 도감

캔뱃지를 제외한 장송의 프리렌 굿즈를 관리하는 반응형 웹앱 스타터입니다.

## 포함 기능
- 9개 카테고리: 피규어, 가챠·캡슐토이, 아크릴·키링, 봉제·인형, 카드·브로마이드, 생활 잡화, 의류·패션, 특전·한정 굿즈, 기타
- 상품 등록·수정, 캐릭터/시리즈, 구매처/날짜/가격, 메모
- 소장/위시리스트/미소장 상태와 수량
- 이미지 URL 또는 최대 2MB 실물 사진 업로드
- 검색, 카테고리/상태 필터, 정렬
- JSON 백업/복원
- 기본 브라우저 저장, 선택적 Supabase 테이블 연결
- 샘플 데이터는 `예시`로 표시되며 공식 상품 DB가 아닙니다.

## 실행
1. `index.html`을 최신 Chrome/Edge에서 엽니다.
2. 브라우저 저장만으로 기본 기능을 사용할 수 있습니다.
3. 다른 기기 동기화가 필요하면 아래 Supabase 설정을 진행합니다.

## Supabase 연결 설정 (기본 테이블 방식)
1. https://supabase.com 에서 프로젝트를 생성합니다.
2. SQL Editor에서 다음 SQL을 실행합니다.

```sql
create table if not exists public.frieren_archive (
  id text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.frieren_archive enable row level security;
```

3. 현재 앱의 기본 연결 방식은 `id = default` 한 레코드를 읽고 쓰는 단순 스타터입니다. Supabase 프로젝트 URL과 anon/publishable key를 앱의 `클라우드 설정`에 넣으면 연결을 시도합니다.

### 보안상 중요한 점
이 스타터는 로그인 및 사용자별 권한 정책을 포함하지 않습니다. 따라서 **개인 데이터가 있는 실제 서비스로 공개 배포하기 전에 반드시 Supabase Auth와 사용자별 RLS 정책을 구현해야 합니다.** 테이블에 무조건적인 public read/write 정책을 추가하지 마세요. 프론트엔드에 service_role/secret key를 절대 넣지 마세요.

실서비스 권장 스키마 예:
```sql
create table public.frieren_collections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique(user_id)
);
alter table public.frieren_collections enable row level security;
create policy "read own collection" on public.frieren_collections
for select to authenticated using (auth.uid() = user_id);
create policy "insert own collection" on public.frieren_collections
for insert to authenticated with check (auth.uid() = user_id);
create policy "update own collection" on public.frieren_collections
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
```
위 권장 스키마를 사용하려면 앱 코드도 로그인 세션과 `user_id` 기준 쿼리를 사용하도록 수정해야 합니다. 현재 제공된 앱은 그 인증 흐름을 아직 구현하지 않았습니다.

## 배포
정적 웹사이트로 배포할 수 있습니다. 예: GitHub Pages, Netlify, Vercel. `index.html`을 업로드하면 UI를 호스팅할 수 있습니다. 브라우저 저장은 브라우저/기기별이며, 진짜 클라우드 동기화는 위 연결 및 보안 작업이 완료되어야 합니다.

## 데이터와 이미지
- 초기 샘플은 화면 기능 확인용이며 실제 공식 상품명·사진이 아닙니다.
- 사진 업로드는 브라우저 저장소에 Data URL로 저장되므로 사진이 많으면 저장 공간이 빠르게 찰 수 있습니다. 작은 이미지나 이미지 URL을 권장합니다.
- 정기적으로 JSON 백업을 내보내세요.


## 자동 공식 굿즈 도감 (실험 기능)

프로젝트에 다음 파일이 추가되었습니다.
- `catalog.html`: 자동 수집 목록을 검색·분류하고 내 컬렉션/위시리스트에 추가하는 화면
- `catalog_sync.py`: 공식 목록 페이지에서 상품명, 원본 URL, 가능한 경우 이미지 URL을 수집
- `sources.json`: 수집 대상 공식 출처 및 허용 제조사 도메인
- `.github/workflows/catalog-sync.yml`: GitHub Actions에서 매일 자동 실행
- `catalog.json`: 수집 결과 데이터

### 매일 자동 수집을 켜는 방법
1. 이 폴더를 GitHub 저장소에 업로드합니다.
2. 저장소의 **Settings → Actions → General**에서 workflow가 저장소에 쓰기 권한을 갖도록 설정합니다(필요한 경우).
3. **Actions** 탭에서 `Update official goods catalog`를 선택하고 `Run workflow`로 최초 실행을 시험합니다.
4. 실행 로그와 `catalog.json`을 확인한 뒤, 정적 사이트를 GitHub Pages/Netlify/Vercel 등에 배포합니다.
5. 배포 주소에서 `catalog.html`을 열어 목록과 `내 컬렉션에 추가` 동작을 확인합니다.

GitHub Actions 일정은 UTC 기준 매일 18:17(한국 시간 다음 날 03:17)에 실행됩니다. 예약 실행은 GitHub Actions 사용량/정책에 따라 지연될 수 있습니다. 자동 수집은 서버에서 수행되므로 `index.html`을 파일로 직접 열어서는 최신 `catalog.json`을 불러올 수 없습니다. 웹 호스팅 주소로 접속하세요.

### 현재 수집기의 범위와 한계
- 첫 기본 출처는 [애니메이션 공식 GOODS](https://frieren-anime.jp/goods/)입니다. 공식 목록 페이지의 링크/메타데이터에서 읽을 수 있는 정보를 보수적으로 수집합니다.
- 제조사 도메인은 `sources.json`에 허용 목록으로 준비되어 있지만, 현재 자동으로 따라가는 링크는 공식 GOODS 페이지에서 발견되고 프리렌 관련 텍스트가 있는 링크에 한정됩니다. 제조사별 목록을 더 넓게 수집하려면 해당 제조사의 실제 상품 목록 URL과 사이트 구조에 맞는 파서를 추가해야 합니다.
- 웹페이지 구조, 자바스크립트 렌더링, robots.txt 및 이용약관에 따라 일부 상품은 수집되지 않을 수 있습니다. 수집 성공을 보장하지 않습니다.
- 발매일, 가격, 제조사, 시리즈는 출처 페이지에서 신뢰할 수 있게 확인되지 않으면 `미확인`으로 남습니다. 공식 사이트에 링크가 있다는 것만으로 각 필드가 모두 검증된 것은 아닙니다.
- 캔뱃지는 일본어/한국어/영어 키워드로 제외하지만, 이름이 모호하거나 번역된 상품은 자동 분류가 틀릴 수 있으므로 결과를 확인해야 합니다.
- 이미지는 원본 사이트 URL을 참조하며 프로젝트가 이미지 권리를 소유한다는 뜻은 아닙니다. 사이트 정책을 확인하고 이미지를 무단 복제·재호스팅하지 마세요.
- `catalog.html`의 컬렉션 추가는 같은 웹 출처의 브라우저 `localStorage`에 저장합니다. 기존 도감이 Supabase를 사용하더라도 이 기능이 Supabase 동기화로 직접 추가되지는 않습니다. 멀티기기 동기화를 원하면 인증된 백엔드 API/DB 연결을 별도로 구현해야 합니다.
- 중복은 우선 원본 URL과 catalog ID로 검사합니다. 서로 다른 URL에서 같은 상품이 올라오는 경우를 완벽히 잡지는 못합니다.
- 이 기능은 초기 프로토타입입니다. 자동 수집 결과는 게시 전에 검토하고, 실제 공개 서비스에서는 공식 API/허가된 데이터 소스를 우선 사용하세요.
