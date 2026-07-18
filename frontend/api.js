// 八马茶语 API 封装层
// 所有后端调用集中在此，前端通过 BAMA_API.xxx() 调用
const BAMA_API=(function(){
  const BASE="http://localhost:8000";

  // 茶名→tea_id 映射（仅来源于后端 /api/teas，无任何兜底）
  let TEA_ID_MAP={};

  // GIFT_SCENES value → 后端 recipient 中文 label
  const GIFT_TO_RECIPIENT={
    "self":"自己喝",
    "elder":"送长辈",
    "colleague":"送同事",
    "friend":"送朋友",
    "business":"商务送礼"
  };

  async function request(method, path, body){
    const url=BASE+path;
    const opts={
      method,
      headers:{"Content-Type":"application/json"},
      signal:AbortSignal.timeout(310000) // 310s 超时，适配生图
    };
    if(body)opts.body=JSON.stringify(body);
    let res;
    try{
      res=await fetch(url, opts);
    }catch(e){
      throw new Error("网络请求失败："+e.message+"（请确认后端已启动在 "+BASE+"）");
    }
    let json;
    try{
      json=await res.json();
    }catch(e){
      throw new Error("响应解析失败：HTTP "+res.status);
    }
    if(!res.ok||!json.success){
      const msg=json.error&&json.error.message?("后端错误["+json.error.code+"]："+json.error.message):("HTTP "+res.status);
      throw new Error(msg);
    }
    return json;
  }

  // 初始化：从后端获取茶品列表建立映射（失败即抛错，不兜底）
  async function init(){
    const r=await request("GET","/api/teas");
    if(r.data&&Array.isArray(r.data)){
      r.data.forEach(t=>{
        if(t.id&&t.name)TEA_ID_MAP[t.name]=t.id;
      });
    }
    console.log("[BAMA_API] 茶品映射已加载:", TEA_ID_MAP);
  }

  function getTeaId(teaName){
    const id=TEA_ID_MAP[teaName];
    if(!id){
      throw new Error("未在 /api/teas 找到茶品「"+teaName+"」的映射，拒绝兜底");
    }
    return id;
  }

  function giftToRecipient(giftValue){
    return GIFT_TO_RECIPIENT[giftValue]||"";
  }

  // 1. 获取茶品列表
  async function getTeas(){
    return request("GET","/api/teas");
  }

  // 2. 国内文案生成
  async function domesticExpression(teaName, sel){
    const teaId=getTeaId(teaName);
    const body={
      audience:{
        knowledge_level: sel.targetConsumer==="入门"?"beginner":(sel.targetConsumer==="专业"?"expert":"intermediate"),
        scenario: "store_sales",
        psychology: ""
      },
      style: "store_sales",
      tone: sel.tone||undefined,
      length: sel.length||undefined,
      time_node: sel.timeNode||undefined,
      task_type: sel.taskType||undefined,
      flavor_reference: sel.flavorReference||undefined,
      recipient: giftToRecipient(sel.giftScene)||undefined
    };
    // 清理 undefined
    Object.keys(body).forEach(k=>body[k]===undefined&&delete body[k]);
    return request("POST", `/api/teas/${teaId}/domestic-expression`, body);
  }

  // 3. 海外文案生成
  async function crossCulturalExpression(teaName, sel){
    const teaId=getTeaId(teaName);
    const body={
      target_language: sel.language||"en",
      market: "western",
      audience_reference: "specialty_coffee_lovers",
      audience_level: sel.targetConsumer==="入门"?"beginner":(sel.targetConsumer==="专业"?"expert":"intermediate"),
      preserve_chinese_terms: true,
      tone: sel.tone||undefined,
      length: sel.length||undefined,
      time_node: sel.timeNode||undefined,
      task_type: sel.taskType||undefined,
      flavor_reference: sel.flavorReference||undefined,
      recipient: giftToRecipient(sel.giftScene)||undefined
    };
    Object.keys(body).forEach(k=>body[k]===undefined&&delete body[k]);
    return request("POST", `/api/teas/${teaId}/cross-cultural-expression`, body);
  }

  // 4. 物料数据生成（第一步）
  async function marketingAsset(teaName, sel, routeId){
    const teaId=getTeaId(teaName);
    const body={
      route_id: routeId||("demo_"+teaId),
      asset_type: "poster",
      platform: sel.platform||undefined,
      language: sel.language||"zh",
      style: sel.style||undefined,
      content_theme: sel.content?(sel.content.replace(/-/g,"_")):undefined
    };
    Object.keys(body).forEach(k=>body[k]===undefined&&delete body[k]);
    return request("POST", `/api/teas/${teaId}/marketing-asset`, body);
  }

  // 5. 真实生图（第二步）
  async function imageGenerate(prompt, teaName, sel, routeId){
    const teaId=getTeaId(teaName);
    const body={
      prompt: prompt,
      size: "1K",
      style: sel.style==="商务"?"business":"fresh",
      scene: "closeup",
      tea_id: teaId,
      language: sel.language||"zh",
      route_id: routeId||("demo_"+teaId)
    };
    return request("POST", "/api/image/generate", body);
  }

  // 6. 追溯链
  async function getTrace(outputId){
    return request("GET", `/api/trace/${outputId}`);
  }

  return {
    init, getTeaId, giftToRecipient,
    getTeas, domesticExpression, crossCulturalExpression,
    marketingAsset, imageGenerate, getTrace
  };
})();

// 启动时自动初始化
if(typeof window!=="undefined"){
  window.addEventListener("DOMContentLoaded",()=>BAMA_API.init());
}
