/**
 * botScript.ts — JavaScript strings injected into the Naukri WebView.
 * Mirrors the Python bot's Selenium commands exactly:
 *   loginScript()        ↔  _login_with_native_credentials()
 *   SCRAPE_JOBS_SCRIPT   ↔  get_recommended_jobs()
 *   EASY_APPLY_SCRIPT    ↔  apply_to_job() → Easy Apply path
 */

export const NAUKRI = {
  LOGIN:       'https://www.naukri.com/nlogin/login',
  RECOMMENDED: 'https://www.naukri.com/mnjuser/recommendedjobs',
};

export interface ScrapedJob {
  jobId:    string;
  title:    string;
  company:  string;
  location: string;
  skills:   string;
  url:      string;
}

export type BotMsg =
  | { type: 'jobs';    jobs: ScrapedJob[] }
  | { type: 'applied'; title: string }
  | { type: 'skipped'; reason: string }
  | { type: 'error';   message: string };

// ── Login script — mirrors _login_with_native_credentials() ──────────────────
export function loginScript(email: string, password: string): string {
  return `(function(){
  function set(el,v){
    try{
      var s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
      s.call(el,v);
      el.dispatchEvent(new Event('input',{bubbles:true}));
      el.dispatchEvent(new Event('change',{bubbles:true}));
    }catch(e){el.value=v;}
  }
  var n=0,iv=setInterval(function(){
    n++;
    if(n>80){
      clearInterval(iv);
      window.ReactNativeWebView.postMessage(JSON.stringify({type:'error',message:'Login form not found after 16s'}));
      return;
    }
    var e=document.getElementById('usernameField')
      ||document.querySelector('input[placeholder*="Email" i]')
      ||document.querySelector('input[type="email"]');
    var p=document.getElementById('passwordField')
      ||document.querySelector('input[type="password"]');
    if(e&&p){
      clearInterval(iv);
      set(e,${JSON.stringify(email)});
      setTimeout(function(){
        set(p,${JSON.stringify(password)});
        setTimeout(function(){
          var b=document.querySelector('button[type="submit"]')
            ||document.querySelector('[class*="loginButton"]')
            ||document.querySelector('[class*="login-btn"]');
          if(b)b.click();
          else if(p.form)p.form.submit();
        },500);
      },400);
    }
  },200);
})(); true;`;
}

// ── Scrape recommended jobs — mirrors get_recommended_jobs() ─────────────────
export const SCRAPE_JOBS_SCRIPT = `(function(){
  var jobs=[],seen=new Set();
  var cards=Array.from(document.querySelectorAll(
    'article[data-job-id],[class*="jobTuple"],[class*="job-tuple"],[class*="cust-job-tuple"]'
  ));
  if(!cards.length){
    cards=Array.from(document.querySelectorAll('[class*="job"][class*="card"],li[class*="job"]'));
  }
  cards.forEach(function(c){
    var ta=c.querySelector('[class*="title" i] a,h2 a,a[title][href*="job"]');
    var id=c.getAttribute('data-job-id')||'';
    var url=ta?(ta.getAttribute('href')||''):'';
    if(url&&!url.startsWith('http'))url='https://www.naukri.com'+url;
    if(!id)id=(url.match(/-(\\d{8,})[?]/)||url.match(/-(\\d{8,})$/)|| [])[1]||url;
    if(ta&&url&&!seen.has(id)){
      seen.add(id);
      var comp=c.querySelector('[class*="comp" i],[class*="company" i]');
      var loc=c.querySelector('[class*="location" i],[class*="loc" i]');
      var sk=c.querySelector('[class*="skill" i],[class*="tag" i]');
      jobs.push({
        jobId:id,
        title:ta.innerText.trim(),
        company:comp?comp.innerText.trim().split('\\n')[0]:'',
        location:loc?loc.innerText.trim():'',
        skills:sk?sk.innerText.trim():'',
        url:url
      });
    }
  });
  window.ReactNativeWebView.postMessage(JSON.stringify({type:'jobs',jobs:jobs}));
  true;
})(); true;`;

// ── Easy Apply — mirrors apply_to_job() Easy Apply path ─────────────────────
export const EASY_APPLY_SCRIPT = `(function(){
  var SELS=[
    '[class*="apply-button" i]:not([class*="ext" i])',
    'button[id*="apply" i]:not([id*="ext" i])',
    '[class*="easy-apply" i]',
    '[class*="applyBtn" i]:not([class*="ext" i])',
    'a[id*="apply" i]:not([href*="external"])'
  ];
  var btn=null;
  for(var i=0;i<SELS.length;i++){
    var els=Array.from(document.querySelectorAll(SELS[i]));
    for(var j=0;j<els.length;j++){
      var el=els[j];
      if(el.offsetParent!==null&&!/external/i.test(el.innerText||el.textContent||'')){
        btn=el;break;
      }
    }
    if(btn)break;
  }
  if(btn){
    btn.scrollIntoView({behavior:'smooth',block:'center'});
    setTimeout(function(){
      btn.click();
      window.ReactNativeWebView.postMessage(JSON.stringify({type:'applied',title:document.title}));
    },400);
  } else {
    window.ReactNativeWebView.postMessage(JSON.stringify({type:'skipped',reason:'No Easy Apply button — external application'}));
  }
  true;
})(); true;`;

// ── Confirm apply modal — click "Apply" in the Easy Apply dialog ─────────────
export const CONFIRM_APPLY_SCRIPT = `(function(){
  var btn=document.querySelector('[class*="submit" i],[class*="confirm" i],[class*="apply" i]');
  if(btn&&btn.offsetParent!==null){
    btn.click();
    window.ReactNativeWebView.postMessage(JSON.stringify({type:'applied',title:'confirmed'}));
  }
  true;
})(); true;`;
