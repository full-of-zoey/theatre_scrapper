const express = require('express');
const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');
const { createWorker } = require('tesseract.js');
const sharp = require('sharp');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 데이터 저장 디렉토리 생성
const DATA_DIR = path.join(__dirname, 'performances');
fs.mkdir(DATA_DIR, { recursive: true }).catch(console.error);

// 웹 스크래핑 엔드포인트
app.post('/api/scrape', async (req, res) => {
  const { url } = req.body;
  
  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    // 페이지 콘텐츠 가져오기
    const html = await page.content();
    const $ = cheerio.load(html);
    
    // 페이지 텍스트 추출
    const pageText = await page.evaluate(() => {
      // 모든 텍스트 콘텐츠 가져오기 (숨겨진 요소 포함)
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );
      const texts = [];
      let node;
      while (node = walker.nextNode()) {
        const text = node.textContent.trim();
        if (text) texts.push(text);
      }
      return texts.join(' ');
    });
    
    // 포스터 이미지 찾기 및 OCR 처리
    let ocrText = '';
    const posterUrls = await extractPosterImages($, page, url);
    if (posterUrls.length > 0) {
      console.log('Found poster images:', posterUrls.length);
      // OCR 성능 문제로 임시 비활성화
      // ocrText = await performOCR(posterUrls[0]);
    }
    
    // 공연 정보 추출
    const combinedText = pageText + ' ' + ocrText;
    
    const performance = {
      url: url,
      scrapedAt: new Date().toISOString(),
      title: extractTitle($, pageText),
      date: extractDate($, pageText) || extractDateFromOCR(ocrText),
      venue: extractVenue($, pageText) || extractVenueFromOCR(ocrText),
      performers: extractPerformers($, pageText + ' ' + ocrText),
      program: extractProgram($, pageText + ' ' + ocrText),
      description: extractDescription($),
      price: extractPrice($, pageText),
      posterImage: posterUrls[0] || '',
      ocrExtracted: ocrText ? true : false,
      rawText: combinedText.replace(/\s+/g, ' ').trim().substring(0, 5000)
    };
    
    await browser.close();
    
    // 데이터 저장
    const filename = `performance_${Date.now()}.json`;
    const filepath = path.join(DATA_DIR, filename);
    await fs.writeFile(filepath, JSON.stringify(performance, null, 2));
    
    res.json({ 
      success: true, 
      data: performance,
      savedAs: filename 
    });
    
  } catch (error) {
    console.error('Scraping error:', error);
    res.status(500).json({ 
      error: 'Failed to scrape the webpage',
      details: error.message 
    });
  }
});

// 저장된 공연 목록 조회
app.get('/api/performances', async (req, res) => {
  try {
    const files = await fs.readdir(DATA_DIR);
    const performances = [];
    
    for (const file of files) {
      if (file.endsWith('.json')) {
        const content = await fs.readFile(path.join(DATA_DIR, file), 'utf-8');
        const performance = JSON.parse(content);
        performance.id = file.replace('.json', '');
        performances.push(performance);
      }
    }
    
    performances.sort((a, b) => new Date(b.scrapedAt) - new Date(a.scrapedAt));
    res.json(performances);
    
  } catch (error) {
    console.error('Error reading performances:', error);
    res.status(500).json({ error: 'Failed to load performances' });
  }
});

// 특정 공연 상세 조회
app.get('/api/performances/:id', async (req, res) => {
  try {
    const filepath = path.join(DATA_DIR, `${req.params.id}.json`);
    const content = await fs.readFile(filepath, 'utf-8');
    res.json(JSON.parse(content));
  } catch (error) {
    res.status(404).json({ error: 'Performance not found' });
  }
});

// 공연 삭제
app.delete('/api/performances/:id', async (req, res) => {
  try {
    const filepath = path.join(DATA_DIR, `${req.params.id}.json`);
    await fs.unlink(filepath);
    res.json({ success: true });
  } catch (error) {
    res.status(404).json({ error: 'Performance not found' });
  }
});

// 포스터 이미지 추출
async function extractPosterImages($, page, url) {
  const posterUrls = [];
  
  // 일반적인 포스터 이미지 셀렉터
  const posterSelectors = [
    '.poster img', '.main-image img', '.visual img', 
    '.detail_poster img', '.prf_poster img', '[class*="poster"] img',
    '.thumb img', '.performance-image img', 'meta[property="og:image"]'
  ];
  
  // 셀렉터로 이미지 찾기
  for (const selector of posterSelectors) {
    if (selector.includes('meta')) {
      const metaContent = $(selector).attr('content');
      if (metaContent) {
        posterUrls.push(metaContent);
      }
    } else {
      $(selector).each((i, el) => {
        const src = $(el).attr('src') || $(el).attr('data-src');
        if (src) {
          // 상대 경로를 절대 경로로 변환
          const absoluteUrl = new URL(src, url).href;
          if (!posterUrls.includes(absoluteUrl)) {
            posterUrls.push(absoluteUrl);
          }
        }
      });
    }
  }
  
  // Puppeteer로 추가 이미지 찾기
  try {
    const images = await page.evaluate(() => {
      const imgs = [];
      document.querySelectorAll('img').forEach(img => {
        if (img.naturalWidth > 300 && img.naturalHeight > 300) { // 포스터 크기 필터
          const src = img.src || img.dataset.src;
          if (src && (src.includes('poster') || src.includes('main') || 
                     src.includes('visual') || src.includes('performance'))) {
            imgs.push(src);
          }
        }
      });
      return imgs;
    });
    
    images.forEach(src => {
      if (!posterUrls.includes(src)) {
        posterUrls.push(src);
      }
    });
  } catch (e) {
    console.error('Error finding images with Puppeteer:', e);
  }
  
  return posterUrls.slice(0, 3); // 최대 3개 포스터
}

// OCR 수행
async function performOCR(imageUrl) {
  try {
    console.log('Performing OCR on:', imageUrl);
    
    // 이미지 다운로드
    const response = await fetch(imageUrl);
    const buffer = await response.arrayBuffer();
    const imageBuffer = Buffer.from(buffer);
    
    // 이미지 전처리 (선명도 향상)
    const processedImage = await sharp(imageBuffer)
      .resize(2000, null, { withoutEnlargement: true })
      .sharpen()
      .greyscale()
      .normalize()
      .toBuffer();
    
    // Tesseract OCR 실행
    const worker = await createWorker('kor+eng');
    const { data: { text } } = await worker.recognize(processedImage);
    await worker.terminate();
    
    console.log('OCR extracted text length:', text.length);
    return text;
  } catch (error) {
    console.error('OCR error:', error);
    return '';
  }
}

// OCR 텍스트에서 날짜 추출
function extractDateFromOCR(ocrText) {
  if (!ocrText) return '';
  
  const datePatterns = [
    /\d{4}[\.\-\/]\d{1,2}[\.\-\/]\d{1,2}/,
    /\d{4}년\s*\d{1,2}월\s*\d{1,2}일/,
    /\d{1,2}월\s*\d{1,2}일/
  ];
  
  for (const pattern of datePatterns) {
    const match = ocrText.match(pattern);
    if (match) return match[0];
  }
  return '';
}

// OCR 텍스트에서 장소 추출
function extractVenueFromOCR(ocrText) {
  if (!ocrText) return '';
  
  const venues = [
    '예술의전당', '롯데콘서트홀', '세종문화회관', '통영국제음악당',
    'LG아트센터', '금호아트홀', '블루스퀘어'
  ];
  
  for (const venue of venues) {
    if (ocrText.includes(venue)) {
      const regex = new RegExp(`${venue}[^\n]{0,20}`, 'g');
      const match = ocrText.match(regex);
      if (match) return match[0].trim();
    }
  }
  return '';
}

// 제목 추출 개선
function extractTitle($, pageText) {
  // 특정 패턴으로 제목 찾기
  const titlePatterns = [
    /정명훈\s*&\s*원\s*코리아\s*오케스트라\s*<[^>]+>/,
    /[^\n]{3,100}(?:<[^\n]+>)/,
    /[^\n]{3,100}(?:《[^》]+》)/
  ];
  
  for (const pattern of titlePatterns) {
    const match = pageText.match(pattern);
    if (match) return match[0].trim();
  }
  
  // 기존 셀렉터 방식
  const titleSelectors = [
    'h1', '.concert_title', '.performance_title', '.prf_title',
    '[class*="title"]', 'title', '.title'
  ];
  
  for (const selector of titleSelectors) {
    const title = $(selector).first().text().trim();
    if (title && title.length > 5) return title;
  }
  
  return '';
}

// 데이터 추출 헬퍼 함수들
function extractDate($, pageText = '') {
  // 더 정밀한 날짜 및 시간 패턴
  const dateTimePatterns = [
    /\d{4}[\.\-\/]\d{1,2}[\.\-\/]\d{1,2}\s*\(?[월화수목금토일]\)?\s*\d{1,2}[:\s]*\d{2}/,
    /\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*\(?[월화수목금토일]\)?\s*[오전후]*\s*\d{1,2}[시:\s]*\d{2}[분]*/,
    /\d{1,2}월\s*\d{1,2}일\s*\(?[월화수목금토일]\)?\s*\d{1,2}[:\s]*\d{2}/,
    /\d{4}[\.\-\/]\d{1,2}[\.\-\/]\d{1,2}/,
    /\d{4}년\s*\d{1,2}월\s*\d{1,2}일/
  ];
  
  const text = pageText || $('body').text();
  
  // 시간 패턴 별도 추출
  const timePatterns = [
    /[오전후]*\s*\d{1,2}[시:\s]+\d{2}[분]*/,
    /\d{1,2}:\d{2}\s*[APMP\.]+/,
    /\d{1,2}:\d{2}/
  ];
  
  let dateResult = '';
  let timeResult = '';
  
  // 날짜 추출
  for (const pattern of dateTimePatterns) {
    const match = text.match(pattern);
    if (match) {
      dateResult = match[0];
      break;
    }
  }
  
  // 시간 별도 추출 시도
  if (!dateResult.match(/\d{1,2}[:\s]\d{2}/)) {
    for (const pattern of timePatterns) {
      const match = text.match(pattern);
      if (match) {
        timeResult = match[0];
        break;
      }
    }
  }
  
  // 구조화된 요소에서 찾기
  const dateSelectors = [
    '.prf_date', '.date', '.performanceDate', '.event-date', 
    '.performance-date', '.concert-date', 'time', '[class*="date"]',
    '.info_detail li:contains("일시")', '.detail_info span'
  ];
  
  if (!dateResult) {
    for (const selector of dateSelectors) {
      try {
        const date = $(selector).first().text().trim();
        if (date && date.match(/\d{2,4}/)) {
          dateResult = date;
          break;
        }
      } catch (e) {}
    }
  }
  
  return timeResult ? `${dateResult} ${timeResult}`.trim() : dateResult;
}

function extractVenue($, pageText = '') {
  // 특정 공연장 이름들
  const knownVenues = [
    '예술의전당', 'SAC', '콘서트홀', '리사이틀홀', 'IBK챔버홀',
    '롯데콘서트홀', '세종문화회관', '통영국제음악당', '대구콘서트하우스',
    '아트센터', '오페라하우스', '음악당', 'LG아트센터', '블루스퀘어',
    '금호아트홀', '예술의 전당', 'Seoul Arts Center'
  ];
  
  const text = pageText || $('body').text();
  
  // 알려진 공연장 먼저 찾기
  for (const venue of knownVenues) {
    const regex = new RegExp(`${venue}[^\\n\\r]{0,30}`, 'gi');
    const match = text.match(regex);
    if (match) {
      // 홀 이름까지 포함해서 추출
      const hallPattern = /(.*?(?:홀|Hall|하우스|House|극장|Theater|당|Center)[^\\n\\r]{0,10})/i;
      const hallMatch = match[0].match(hallPattern);
      if (hallMatch) return hallMatch[0].trim();
      return match[0].trim();
    }
  }
  
  // 구조화된 요소에서 찾기
  const venueSelectors = [
    '.prf_place', '.venue', '.location', '.place', '.hall',
    '.concert-hall', '[class*="venue"]', '[class*="place"]',
    '.info_detail li:contains("장소")', '.theater_name',
    'span:contains("공연장")', 'dd:contains("홀")'
  ];
  
  for (const selector of venueSelectors) {
    try {
      const venue = $(selector).first().text().trim();
      if (venue && venue.length > 2) return venue;
    } catch (e) {}
  }
  
  // 키워드 기반 추출
  const venueKeywords = ['장소', '공연장', 'venue', 'location', '홀', 'hall'];
  for (const keyword of venueKeywords) {
    const regex = new RegExp(`${keyword}[\\s:：]+([^\\n\\r]{3,50})`, 'i');
    const match = text.match(regex);
    if (match) return match[1].trim();
  }
  
  return '';
}

function extractPerformers($, ocrText = '') {
  const performers = [];
  const combinedText = $('body').text() + ' ' + ocrText;
  
  // 구조화된 출연진 정보 셀렉터
  const performerSelectors = [
    '.prf_cast', '.performer', '.artist', '.cast', '.musicians',
    '.conductor', '.soloist', '[class*="performer"]', '[class*="artist"]',
    '.info_detail li:contains("출연")', '.cast_list li',
    'dl dt:contains("출연") + dd', '.artist_info'
  ];
  
  performerSelectors.forEach(selector => {
    try {
      $(selector).each((i, el) => {
        const text = $(el).text().trim();
        if (text && text.length > 1 && !performers.includes(text)) {
          performers.push(text);
        }
      });
    } catch (e) {}
  });
  
  const text = combinedText;
  
  // 특정 패턴으로 찾기 (롯데콘서트홀 형식)
  const lotteConcertPatterns = [
    /지휘\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /소프라노\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /메조\s*소프라노\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /테너\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /바리톤\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /연주\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g,
    /합창\s*[|│]\s*([^\n,]+?)(?:\s*[,\n]|$)/g
  ];
  
  const roles = ['지휘', '소프라노', '메조 소프라노', '테너', '바리톤', '연주', '합창'];
  
  lotteConcertPatterns.forEach((pattern, idx) => {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const name = match[1].trim();
      if (name && name.length > 1) {
        // 한글/영문 이름 분리
        const namePattern = /([가-힣]+)\s*([A-Za-z\s\-]+)?/;
        const nameMatch = name.match(namePattern);
        if (nameMatch) {
          const korName = nameMatch[1];
          const engName = nameMatch[2] ? nameMatch[2].trim() : '';
          const fullName = engName ? `${korName} (${engName})` : korName;
          const performerWithRole = `${fullName} - ${roles[idx]}`;
          if (!performers.some(p => p.includes(korName))) {
            performers.push(performerWithRole);
          }
        }
      }
    }
  });
  
  // 역할별 키워드 매칭 (더 정밀하게)
  const rolePatterns = [
    { role: '지휘', patterns: [/지휘[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Conductor[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '피아노', patterns: [/피아노[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Piano[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '바이올린', patterns: [/바이올린[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Violin[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '첼로', patterns: [/첼로[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Cello[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '소프라노', patterns: [/소프라노[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Soprano[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '메조소프라노', patterns: [/메조\s*소프라노[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Mezzo[\s\-]*Soprano[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '테너', patterns: [/테너[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Tenor[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '바리톤', patterns: [/바리톤[\s:：]*([가-힣a-zA-Z\s]+)(?=[,\n]|$)/g, /Baritone[\s:：]*([a-zA-Z\s\-]+)(?=[,\n]|$)/gi] },
    { role: '오케스트라', patterns: [/오케스트라[\s:：]*([가-힣a-zA-Z\s]+오케스트라)(?=[,\n]|$)/g, /Orchestra[\s:：]*([a-zA-Z\s]+Orchestra)(?=[,\n]|$)/gi] },
    { role: '합창단', patterns: [/합창단[\s:：]*([가-힣a-zA-Z\s]+합창단)(?=[,\n]|$)/g, /Choir[\s:：]*([a-zA-Z\s]+Choir)(?=[,\n]|$)/gi] }
  ];
  
  rolePatterns.forEach(({ role, patterns }) => {
    patterns.forEach(pattern => {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        const name = match[1].trim();
        if (name && name.length > 1 && name.length < 50) {
          const performerWithRole = `${name} (${role})`;
          if (!performers.some(p => p.includes(name))) {
            performers.push(performerWithRole);
          }
        }
      }
    });
  });
  
  // 일반 출연진 패턴
  const generalPatterns = [/출연[\s:：]*([^\n]{3,100})/g, /Cast[\s:：]*([^\n]{3,100})/gi];
  generalPatterns.forEach(pattern => {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const names = match[1].split(/[,、]/); 
      names.forEach(name => {
        const trimmed = name.trim();
        if (trimmed && trimmed.length > 1 && trimmed.length < 50 && !performers.some(p => p.includes(trimmed))) {
          performers.push(trimmed);
        }
      });
    }
  });
  
  return performers.slice(0, 20); // 최대 20명까지
}

function extractProgram($, ocrText = '') {
  const programs = [];
  const combinedText = $('body').text() + ' ' + ocrText;
  
  // 구조화된 프로그램 정보 셀렉터
  const programSelectors = [
    '.prf_program', '.program', '.repertoire', '.playlist', '.setlist',
    '.program_list li', '[class*="program"]', '.concert_program',
    '.info_detail li:contains("프로그램")', '.info_detail li:contains("곡목")',
    'dl dt:contains("프로그램") + dd', '.tracklist li'
  ];
  
  programSelectors.forEach(selector => {
    try {
      $(selector).each((i, el) => {
        const text = $(el).text().trim();
        if (text && text.length > 3 && !programs.includes(text)) {
          programs.push(text);
        }
      });
    } catch (e) {}
  });
  
  const text = combinedText;
  
  // 베토벤 교향곡 제9번 패턴
  const beethoven9Patterns = [
    /베토벤\s*교향곡\s*제\s*9번[^\n]{0,50}/gi,
    /Beethoven\s*Symphony\s*No\.?\s*9[^\n]{0,50}/gi,
    /교향곡\s*제\s*9번[^\n]*(?:합창|Choral)/gi,
    /Symphony\s*No\.?\s*9[^\n]*(?:합창|Choral)/gi,
    /베토벤[^\n]{0,30}(?:d단조|D\s*minor)[^\n]{0,30}(?:op\.?\s*125|Op\.?\s*125)/gi
  ];
  
  beethoven9Patterns.forEach(pattern => {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const piece = match[0].trim();
      if (!programs.some(p => p.includes('베토벤') && p.includes('9'))) {
        programs.push(piece);
      }
    }
  });
  
  // OCR 텍스트에서 특별히 찾기
  if (ocrText) {
    // 교향곡 패턴
    const symphonyPattern = /(?:교향곡|Symphony)\s*(?:제|No\.?)?\s*\d+번[^\n]{0,50}/gi;
    const symphonyMatches = ocrText.matchAll(symphonyPattern);
    for (const match of symphonyMatches) {
      if (!programs.includes(match[0])) {
        programs.push(match[0].trim());
      }
    }
    
    // 협주곡 패턴
    const concertoPattern = /(?:[가-힣]+|\w+)?\s*협주곡[^\n]{0,50}/gi;
    const concertoMatches = ocrText.matchAll(concertoPattern);
    for (const match of concertoMatches) {
      if (!programs.includes(match[0])) {
        programs.push(match[0].trim());
      }
    }
  }
  
  // 확장된 작곡가 목록
  const composers = [
    'Bach', 'Mozart', 'Beethoven', 'Brahms', 'Chopin', 'Schubert', 'Schumann', 
    'Liszt', 'Wagner', 'Verdi', 'Puccini', 'Debussy', 'Ravel', 'Stravinsky', 
    'Prokofiev', 'Shostakovich', 'Tchaikovsky', 'Rachmaninoff', 'Mahler',
    'Haydn', 'Handel', 'Vivaldi', 'Mendelssohn', 'Dvorak', 'Sibelius',
    'Grieg', 'Saint-Saens', 'Berlioz', 'Rossini', 'Strauss', 'Bartok',
    '바흐', '모차르트', '베토벤', '브람스', '쇼팽', '슈베르트', '슈만',
    '리스트', '바그너', '베르디', '푸치니', '드뷔시', '라벨', '차이콥스키',
    '라흐마니노프', '말러', '하이든', '헨델', '비발디', '멘델스존'
  ];
  
  // 작품 번호 패턴 포함
  const opusPatterns = [
    'Op\\.\\s*\\d+', 'BWV\\s*\\d+', 'K\\.\\s*\\d+', 'D\\.\\s*\\d+', 
    'Hob\\.\\s*[IVX]+', 'No\\.\\s*\\d+', '작품\\s*\\d+'
  ];
  
  // 작곡가별 곡 찾기
  composers.forEach(composer => {
    const escapedComposer = composer.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(
      `${escapedComposer}[\\s:：,\\-]*([^\\n\\r]{3,150})`, 
      'gi'
    );
    const matches = text.matchAll(pattern);
    
    for (const match of matches) {
      let piece = match[0].trim();
      
      // 작품번호가 있으면 포함
      opusPatterns.forEach(opusPattern => {
        const opusRegex = new RegExp(opusPattern, 'i');
        if (piece.match(opusRegex)) {
          piece = piece.substring(0, piece.search(opusRegex) + piece.match(opusRegex)[0].length + 20);
        }
      });
      
      // 중복 제거 및 길이 체크
      if (piece.length > 5 && piece.length < 200 && !programs.some(p => p.includes(piece.substring(0, 30)))) {
        programs.push(piece);
      }
    }
  });
  
  // 프로그램/곡목 키워드 패턴
  const programKeywords = ['프로그램', '곡목', 'Program', 'Repertoire'];
  programKeywords.forEach(keyword => {
    const regex = new RegExp(`${keyword}[\\s:：]+([^\\n]+)`, 'gi');
    const matches = text.matchAll(regex);
    for (const match of matches) {
      const items = match[1].split(/[,、·]/); 
      items.forEach(item => {
        const trimmed = item.trim();
        if (trimmed && trimmed.length > 5 && trimmed.length < 150 && !programs.includes(trimmed)) {
          programs.push(trimmed);
        }
      });
    }
  });
  
  // 곡 형식 패턴 (소나타, 협주곡 등)
  const formPatterns = [
    /(?:피아노|바이올린|첼로)?\s*(?:소나타|협주곡|교향곡|현악\s*사중주|삼중주)\s*(?:제?\s*\d+번)?[^\n\r]{0,50}/gi,
    /(?:Piano|Violin|Cello)?\s*(?:Sonata|Concerto|Symphony|String\s*Quartet|Trio)\s*(?:No\.?\s*\d+)?[^\n\r]{0,50}/gi
  ];
  
  formPatterns.forEach(pattern => {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const piece = match[0].trim();
      if (piece.length > 5 && !programs.some(p => p.includes(piece.substring(0, 20)))) {
        programs.push(piece);
      }
    }
  });
  
  return programs.slice(0, 30); // 최대 30개 곡목
}

function extractDescription($) {
  // 설명 텍스트 추출
  const descSelectors = ['.description', '.summary', '.overview', '.intro', 'article'];
  for (const selector of descSelectors) {
    const desc = $(selector).first().text().trim();
    if (desc && desc.length > 50) {
      return desc.substring(0, 1000);
    }
  }
  
  // 가장 긴 단락 찾기
  let longestP = '';
  $('p').each((i, el) => {
    const text = $(el).text().trim();
    if (text.length > longestP.length) {
      longestP = text;
    }
  });
  
  return longestP.substring(0, 1000);
}

function extractPrice($, pageText = '') {
  const prices = [];
  
  // 구조화된 가격 정보 셀렉터
  const priceSelectors = [
    '.prf_price', '.price', '.ticket-price', '.cost', '.ticket_info',
    '[class*="price"]', '.seat_price', '.info_detail li:contains("가격")',
    '.info_detail li:contains("티켓")', 'dl dt:contains("가격") + dd'
  ];
  
  priceSelectors.forEach(selector => {
    try {
      $(selector).each((i, el) => {
        const text = $(el).text().trim();
        if (text && text.match(/\d/)) {
          prices.push(text);
        }
      });
    } catch (e) {}
  });
  
  const text = pageText || $('body').text();
  
  // 좌석별 가격 패턴
  const seatPricePatterns = [
    /[RSABCVIP]+석[\s:：]*[\d,]+원/g,
    /[RSABCVIP]+[\s:：]*[\d,]+원/g,
    /(?:전석|일반|학생)[\s:：]*[\d,]+원/g,
    /[\d,]+원\s*\([RSABCVIP]+석\)/g
  ];
  
  seatPricePatterns.forEach(pattern => {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      if (!prices.includes(match[0])) {
        prices.push(match[0]);
      }
    }
  });
  
  // 일반 가격 패턴
  const generalPricePatterns = [
    /[\d,]+\s*원/g,
    /₩\s*[\d,]+/g,
    /KRW\s*[\d,]+/gi
  ];
  
  if (prices.length === 0) {
    generalPricePatterns.forEach(pattern => {
      const matches = text.matchAll(pattern);
      let count = 0;
      for (const match of matches) {
        if (count < 10) { // 최대 10개 가격만
          const price = match[0].trim();
          const numValue = parseInt(price.replace(/[^\d]/g, ''));
          // 합리적인 가격 범위 (1000원 ~ 500만원)
          if (numValue >= 1000 && numValue <= 5000000 && !prices.includes(price)) {
            prices.push(price);
            count++;
          }
        }
      }
    });
  }
  
  // 가격 정렬 및 정리
  return prices.slice(0, 10).join(', ');
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});