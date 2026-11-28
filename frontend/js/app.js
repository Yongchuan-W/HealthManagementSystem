/* ==========================================================
   零、登录与首次健康信息填写
   ========================================================== */
const loginView = document.getElementById('loginView');
const onboardingView = document.getElementById('onboardingView');
const appShell = document.getElementById('appShell');
const loginNotice = document.getElementById('loginNotice');

// ---------- 后端接口封装 ----------
// 通过 python web.py 打开时走 /api/*；直接双击 static 版页面（file: 协议）时只能用本地演示逻辑
const IS_FILE_PROTOCOL = window.location.protocol === 'file:';
let serverMode = !IS_FILE_PROTOCOL;
let currentUser = null;

async function api(path, options) {
  const config = Object.assign({ method: 'GET', credentials: 'same-origin' }, options || {});
  if (config.body && typeof config.body !== 'string') {
    config.headers = Object.assign({ 'Content-Type': 'application/json' }, config.headers || {});
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(path, config);
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  return { ok: response.ok, status: response.status, data: data };
}

// ---------- 数据层：内存缓存 + localStorage + 后端整包同步 ----------
const SYNC_KEYS = [
  'profile', 'weightHistory', 'vitalsHistory', 'bp', 'glucose', 'mealLog',
  'moodLog', 'dietActivity', 'sport', 'reminders', 'quickReminders',
  'familyMembers', 'familyRecords', 'preferences', 'femaleProfile',
  'femaleStatus', 'reports', 'beautyPlan', 'sleepLog'
];
const dataCache = Object.create(null);
const OWNER_KEY = 'hm_owner';
let syncTimer = null;
// 当前登录账号的存储目录：不同账号各用一套 hm_<账号>_<key>，互不影响
let dataScope = '';

function scopeSlug(account) {
  return String(account || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
}

function storageKey(key) {
  return dataScope ? 'hm_' + dataScope + '_' + key : 'hm_' + key;
}

// 切换账号时换一整套本地存储目录，并丢掉上一个账号的内存缓存
function useAccountScope(user) {
  const next = scopeSlug(user && user.account);
  if (next === dataScope) return;
  dataScope = next;
  Object.keys(dataCache).forEach(function (key) {
    delete dataCache[key];
  });
}

function loadData(key, fallback) {
  if (Object.prototype.hasOwnProperty.call(dataCache, key)) {
    return dataCache[key];
  }
  try {
    const raw = window.localStorage.getItem(storageKey(key));
    if (raw !== null) {
      const parsed = JSON.parse(raw);
      dataCache[key] = parsed;
      return parsed;
    }
  } catch (error) {
    // 隐私模式或数据损坏时退回默认值
  }
  return fallback;
}

function saveData(key, value) {
  dataCache[key] = value;
  try {
    window.localStorage.setItem(storageKey(key), JSON.stringify(value));
  } catch (error) {
    // 无痕模式等场景下写入失败，忽略即可
  }
  scheduleSync();
}

function hasLocalData() {
  try {
    return window.localStorage.getItem(storageKey('profile')) !== null;
  } catch (error) {
    return false;
  }
}

// 本机缓存属于哪个账号（空表示是接入账号之前的旧版演示数据）
function localOwner() {
  try {
    return window.localStorage.getItem(OWNER_KEY);
  } catch (error) {
    return null;
  }
}

function setLocalOwner(userId) {
  try {
    window.localStorage.setItem(OWNER_KEY, String(userId));
  } catch (error) {
    // 忽略写入失败
  }
}

function clearLocalData() {
  SYNC_KEYS.forEach(function (key) {
    delete dataCache[key];
    try {
      window.localStorage.removeItem(storageKey(key));
      window.localStorage.removeItem('hm_' + key);   // 旧版未分账号的残留
    } catch (error) {
      // 忽略清理失败
    }
  });
  try {
    window.localStorage.removeItem(OWNER_KEY);
    window.localStorage.removeItem(storageKey('chatLog'));
    window.localStorage.removeItem(storageKey('chatSessions'));
    window.localStorage.removeItem('hm_chatLog');
    window.localStorage.removeItem('hm_chatSessions');
  } catch (error) {
    // 忽略清理失败
  }
}

// 旧版本把所有账号都存在同一套 hm_<key> 里：确认属于当前账号时迁到当前账号目录，
// 迁移后删除旧键，避免以后被别的账号再次读走
function adoptLegacyLocalData() {
  if (!dataScope || !currentUser) return;
  const owner = localOwner();
  if (!owner || owner !== String(currentUser.id)) return;
  if (hasLocalData()) return;
  SYNC_KEYS.forEach(function (key) {
    try {
      const raw = window.localStorage.getItem('hm_' + key);
      if (raw === null) return;
      dataCache[key] = JSON.parse(raw);
      window.localStorage.setItem(storageKey(key), raw);
      window.localStorage.removeItem('hm_' + key);
    } catch (error) {
      // 单条损坏就跳过
    }
  });
}

// 账号里是否已经有业务数据（有记录就不再重复引导填写）
function hasAnyRecord() {
  if ((loadData('weightHistory', []) || []).length) return true;
  if ((loadData('mealLog', []) || []).length) return true;
  if (Object.keys(loadData('moodLog', {}) || {}).length) return true;
  if ((loadData('reminders', []) || []).length) return true;
  if ((loadData('familyMembers', []) || []).length) return true;
  const sport = loadData('sport', null);
  return !!(sport && sport.history && Object.keys(sport.history).length);
}

// 每日状态标签以 { 日期: {tags, note} } 存放，提交前转成后端需要的数组
function femaleStatusList() {
  const status = loadData('femaleStatus', {}) || {};
  return Object.keys(status).map(function (date) {
    const entry = status[date] || {};
    return {
      date: date,
      tags: entry.tags || [],
      note: entry.note || '',
      flow: entry.flow || '',
      color: entry.color || '',
      pain: entry.pain || ''
    };
  });
}

// 把当前数据整理成 /api/sync/import 需要的整包
function buildSyncPayload() {
  const glucose = loadData('glucose', null);
  return {
    replace: true,
    profile: loadData('profile', {}) || {},
    weightHistory: loadData('weightHistory', []),
    vitalsHistory: loadData('vitalsHistory', {}),
    bp: loadData('bp', null),
    glucose: (glucose && typeof glucose === 'object') ? glucose.value : glucose,
    dietActivity: loadData('dietActivity', null),
    mealLog: loadData('mealLog', []),
    sport: loadData('sport', {}),
    moodLog: loadData('moodLog', {}),
    familyMembers: loadData('familyMembers', []),
    familyRecords: loadData('familyRecords', []),
    reminders: loadData('reminders', []),
    quickReminders: loadData('quickReminders', []),
    preferences: loadData('preferences', {}),
    female: {
      profile: loadData('femaleProfile', {}),
      status: femaleStatusList()
    },
    reports: loadData('reports', []),
    beautyPlan: loadData('beautyPlan', null),
    sleepLog: loadData('sleepLog', [])
  };
}

// 500ms 内的多次保存合并为一次整包提交，避免频繁请求
function scheduleSync() {
  if (!serverMode || !currentUser) return;
  clearTimeout(syncTimer);
  syncTimer = setTimeout(flushSync, 500);
}

async function flushSync() {
  syncTimer = null;
  if (!serverMode || !currentUser) return false;
  try {
    const result = await api('/api/sync/import', { method: 'POST', body: buildSyncPayload() });
    if (!result.ok) throw new Error(result.data.error || '保存失败');
    return true;
  } catch (error) {
    // 失败时保留本地数据，并明确提示，避免用户以为已经保存
    showToast('数据未能保存到服务器，请检查网络后重试');
    return false;
  }
}

// 服务端整包里是否有真正的业务数据（quickReminders、运动目标为注册时的默认值，不算）
function bundleHasData(bundle) {
  if (!bundle) return false;
  const profile = bundle.profile || {};
  if (profile.nickname || profile.height || profile.weight) return true;
  if ((bundle.weightHistory || []).length) return true;
  if ((bundle.mealLog || []).length) return true;
  if (Object.keys(bundle.moodLog || {}).length) return true;
  if ((bundle.reminders || []).length) return true;
  if ((bundle.familyMembers || []).length) return true;
  if ((bundle.familyRecords || []).length) return true;
  if (Object.keys((bundle.sport || {}).history || {}).length) return true;
  const vitals = bundle.vitalsHistory || {};
  return Object.keys(vitals).some(function (key) {
    return (vitals[key] || []).length > 0;
  });
}

// 用服务端整包覆盖本地缓存
function applyBundle(bundle) {
  const settings = bundle.settings || {};
  let bp = settings.bp || null;
  if (bp && bp.systolic && bp.diastolic) {
    bp = { systolic: bp.systolic, diastolic: bp.diastolic };
  }
  const glucoseState = settings.glucose;
  const glucose = (glucoseState && typeof glucoseState === 'object')
    ? glucoseState.value
    : glucoseState;

  const femaleStatus = {};
  ((bundle.female || {}).status || []).forEach(function (item) {
    if (!item || !item.date) return;
    femaleStatus[item.date] = {
      tags: item.tags || [],
      note: item.note || '',
      flow: item.flow || '',
      color: item.color || '',
      pain: item.pain || ''
    };
  });

  const values = {
    profile: bundle.profile || {},
    weightHistory: bundle.weightHistory || [],
    vitalsHistory: bundle.vitalsHistory || {},
    bp: bp,
    glucose: glucose,
    dietActivity: settings.dietActivity,
    mealLog: bundle.mealLog || [],
    moodLog: bundle.moodLog || {},
    sport: bundle.sport && bundle.sport.goal
      ? bundle.sport
      : { goal: { kcal: 500, steps: 8000, minutes: 60 }, history: {} },
    reminders: bundle.reminders || [],
    quickReminders: bundle.quickReminders || [],
    familyMembers: bundle.familyMembers || [],
    familyRecords: bundle.familyRecords || [],
    preferences: bundle.preferences || {},
    femaleProfile: (bundle.female || {}).profile || {},
    femaleStatus: femaleStatus,
    reports: bundle.reports || [],
    beautyPlan: settings.beautyPlan || null,
    sleepLog: bundle.sleepLog || []
  };

  Object.keys(values).forEach(function (key) {
    if (values[key] === undefined) return;
    dataCache[key] = values[key];
    try {
      window.localStorage.setItem(storageKey(key), JSON.stringify(values[key]));
    } catch (error) {
      // 忽略写入失败
    }
  });
  if (currentUser && currentUser.id) setLocalOwner(currentUser.id);

  // 内存里的运动对象、活动水平也要立即换成新账号的数据
  reloadSportState();
  applyDietActivity();
}

// 登录 / 会话恢复后，从后端取回整包数据；账号为空而本机有旧数据时先迁移
async function hydrateFromServer() {
  if (!serverMode || !currentUser) return;

  adoptLegacyLocalData();

  let bundle = null;
  try {
    const result = await api('/api/sync/export');
    if (result.ok) bundle = result.data;
  } catch (error) {
    return;
  }
  if (!bundle) return;

  // 本机有数据时先迁移：未绑定账号的旧版数据，或属于当前账号但服务器还没有记录
  const owner = localOwner();
  const sameOwner = !!(owner && currentUser && owner === String(currentUser.id));
  const isLegacy = hasLocalData() && !owner;
  if (!bundleHasData(bundle) && (isLegacy || sameOwner)) {
    const pushed = await flushSync();
    if (!pushed) return;   // 推不上去就保留本机数据，不用空数据覆盖
    try {
      const again = await api('/api/sync/export');
      if (again.ok) bundle = again.data;
    } catch (error) {
      // 迁移失败时沿用本机数据
    }
  }

  applyBundle(bundle);
}

// ---------- 登录成功后的页面切换 ----------

function showAuthError(id, message) {
  const box = document.getElementById(id);
  box.hidden = false;
  box.textContent = message;
}

// 登录成功后：档案已填过身高体重（或已有记录）直接进主界面，否则进入信息填写页
// 注意：新注册账号的昵称默认就是账号名，不能只凭昵称判断档案是否填过
function afterLogin(profile) {
  loginView.hidden = true;
  onboardingView.hidden = true;
  // 首屏进入健康数据总览
  enterApp();
  loadProfileView();
  renderVitalRanges();
  switchPage('data');
  window.scrollTo(0, 0);
}

// 刚完成登录：拉取账号信息后决定进入哪个页面
// 已经拿到刚登录的用户信息时直接使用，省掉一次 /api/auth/me 往返
async function afterAuthenticated(knownUser) {
  let profile = null;
  if (knownUser) {
    currentUser = knownUser;
  } else {
    const result = await api('/api/auth/me');
    if (!result.ok) {
      showAuthError('loginError', result.data.error || '会话已失效，请重新登录');
      return false;
    }
    currentUser = result.data.user || currentUser;
    profile = result.data.profile;
  }
  useAccountScope(currentUser);
  // 登录/恢复会话后立刻刷新管理员入口（避免要刷新页面才出现「数据大屏」）
  updateAdminEntry();
  // 记住上次登录的账号名，下次打开只需输密码（密码由浏览器决定是否记住）
  try {
    window.localStorage.setItem('hm_last_account', (currentUser && currentUser.account) || '');
  } catch (error) {}
  await restoreSession(profile);
  return true;
}

// ---------- 运行模式：连后端 / 纯静态演示 ----------
function setServerMode(enabled) {
  serverMode = !!enabled;
  document.getElementById('logoutBtn').hidden = !serverMode;
  document.getElementById('deleteAccountBtn').hidden = !serverMode;
}

function showLoginNotice(message, warn) {
  loginNotice.hidden = false;
  loginNotice.className = warn ? 'login-notice is-warn' : 'login-notice';
  loginNotice.textContent = message;
}

// 没有后端时：隐藏账号密码表单，只留「进入本地演示」，避免任意账号被当成登录成功
function switchToLocalDemo(message, warn) {
  serverMode = false;
  const form = document.getElementById('loginForm');
  form.hidden = true;
  document.getElementById('authModeSwitch').hidden = true;
  document.getElementById('loginError').hidden = true;
  document.getElementById('authTitle').textContent = '本地演示';
  document.getElementById('authSub').textContent = '数据只保存在本机，不会同步';
  document.getElementById('demoEnter').hidden = false;
  showLoginNotice(message, warn);
}

async function detectBackend() {
  try {
    const result = await api('/api/health');
    return !!(result && result.ok && result.data && result.data.ok);
  } catch (error) {
    return false;
  }
}

// 打开页面时先确认后端可用，再恢复已登录的会话
async function bootAuth() {
  if (IS_FILE_PROTOCOL) {
    setServerMode(false);
    switchToLocalDemo('这是静态演示版，没有后端，无法登录指定账号。正式使用请用电脑运行 python web.py，再通过局域网地址访问。', false);
    return;
  }

  // 直接问会话：即使返回 401 也说明后端在线，省掉一次 /api/health 往返
  let result = null;
  try {
    result = await api('/api/auth/me');
  } catch (error) {
    result = null;
  }

  // 只有请求本身失败（网络不通）时，才额外确认后端是否可达
  if (!result) {
    const backendReady = await detectBackend();
    if (!backendReady) {
      setServerMode(false);
      switchToLocalDemo('这个地址没有运行后端服务，无法登录。请用电脑运行 python web.py，再用它提示的局域网地址访问。', true);
      return;
    }
    try {
      result = await api('/api/auth/me');
    } catch (error) {
      result = null;
    }
    if (!result) {
      showLoginNotice('连接后端失败，请确认电脑上的服务仍在运行。', true);
      return;
    }
  }

  setServerMode(true);

  if (result.ok) {
    currentUser = result.data.user || null;
    useAccountScope(currentUser);
    await restoreSession(result.data.profile);
    return;
  }

  // 会话已过期或从未登录：自动填上上次用的账号，只需输密码
  try {
    const last = window.localStorage.getItem('hm_last_account') || '';
    const input = document.getElementById('loginAccount');
    if (last && input && !input.value) {
      input.value = last;
      const pwd = document.getElementById('loginPassword');
      if (pwd) pwd.focus();
    }
  } catch (error) {}
}

document.getElementById('demoEnter').addEventListener('click', function () {
  document.getElementById('loginError').hidden = true;
  afterLogin(loadData('profile', null));
});

// 免登录体验：不校验账号，直接进入本地示例数据
document.getElementById('guestEnter').addEventListener('click', function () {
  setServerMode(false);
  document.getElementById('loginError').hidden = true;
  afterLogin(loadData('profile', null));
  showToast('免登录体验中，数据只保存在本机');
});


// 已登录会话恢复：先取回账号数据，再决定进入哪个页面并重绘
async function restoreSession(profile) {
  await hydrateFromServer();
  // 登录接口不带档案，取回整包后再从本地缓存读一次，避免已填档案的老账号被要求重填
  afterLogin(profile || loadData('profile', null));
  refreshAllViews();
  await loadChatHistory();
}

document.getElementById('logoutBtn').addEventListener('click', async function () {
  // 退出前先确保最后一次修改已经写入服务器，否则直接把本地数据清掉会真的丢失
  const saved = await flushSync();
  if (serverMode && !saved) return;

  if (serverMode) {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (error) {
      // 网络异常时也允许本地退出
    }
  }
  // 清掉本机的账号数据，避免下一个登录的账号读到上一个账号的内容
  clearLocalData();
  window.location.reload();
});

// 注销账号：永久删除服务器上的账号与全部数据
document.getElementById('deleteAccountBtn').addEventListener('click', async function () {
  if (!serverMode || !currentUser) {
    showToast('当前是本地演示模式，没有可注销的账号');
    return;
  }
  if (!window.confirm('注销账号会删除所有历史数据，请确认是否注销')) return;

  const password = window.prompt('请输入当前账号的密码以确认注销：');
  if (!password) return;

  try {
    const result = await api('/api/account', { method: 'DELETE', body: { password: password } });
    if (!result.ok) {
      showToast(result.data.error || '注销失败，请检查密码后重试');
      return;
    }
    clearLocalData();
    window.alert('账号已注销，数据已清除。');
    window.location.reload();
  } catch (error) {
    showToast('网络异常，注销失败，请稍后再试');
  }
});

// 关闭页面或切到后台时，把还没来得及提交的修改补发一次
window.addEventListener('pagehide', function () {
  if (!serverMode || !currentUser) return;
  try {
    const payload = new Blob([JSON.stringify(buildSyncPayload())], { type: 'application/json' });
    navigator.sendBeacon('/api/sync/import', payload);
  } catch (error) {
    // 浏览器不支持时忽略，下次打开仍会同步
  }
});

// 登录 / 注册两种模式共用同一张卡片
let authMode = 'login';

function setAuthMode(mode) {
  authMode = mode;
  const isRegister = mode === 'register';
  document.getElementById('authTitle').textContent = isRegister ? '创建账号' : '欢迎回来';
  document.getElementById('authSub').textContent = isRegister
    ? '注册后数据会保存在你的账号里，换设备也能同步'
    : '登录后开始科学管理你的健康';
  document.getElementById('loginNicknameField').hidden = !isRegister;
  document.getElementById('loginPassword').setAttribute(
    'autocomplete', isRegister ? 'new-password' : 'current-password');
  document.getElementById('authModeSwitch').textContent = isRegister
    ? '已有账号？去登录'
    : '还没有账号？立即注册';
  document.getElementById('loginSubmit').textContent = isRegister ? '注册并登录' : '登录';
  document.getElementById('loginError').hidden = true;
}

document.getElementById('authModeSwitch').addEventListener('click', function () {
  setAuthMode(authMode === 'login' ? 'register' : 'login');
});

// 密码显示 / 隐藏：点击眼睛切换
(function () {
  const pwdInput = document.getElementById('loginPassword');
  const pwdEye = document.getElementById('pwdEye');
  if (!pwdInput || !pwdEye) return;
  pwdEye.addEventListener('click', function () {
    const show = pwdInput.type === 'password';
    pwdInput.type = show ? 'text' : 'password';
    pwdEye.classList.toggle('is-on', show);
    pwdEye.setAttribute('aria-pressed', show ? 'true' : 'false');
    pwdEye.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
    const use = pwdEye.querySelector('use');
    if (use) use.setAttribute('href', show ? '#i-eye' : '#i-eye-off');
    pwdInput.focus();
  });
})();

document.getElementById('loginForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const account = document.getElementById('loginAccount').value.trim();
  const password = document.getElementById('loginPassword').value;
  const nickname = document.getElementById('loginNickname').value.trim();
  const submit = document.getElementById('loginSubmit');
  const isRegister = authMode === 'register';

  if (!account || !password) {
    showAuthError('loginError', '请输入账号与密码');
    return;
  }
  if (isRegister && password.length < 6) {
    showAuthError('loginError', '密码至少 6 位');
    return;
  }

  if (!serverMode) {
    showAuthError('loginError', '当前没有连接到后端，无法登录。');
    return;
  }

  submit.disabled = true;
  submit.textContent = isRegister ? '注册中…' : '登录中…';
  try {
    const result = await api(isRegister ? '/api/auth/register' : '/api/auth/login', {
      method: 'POST',
      body: isRegister ? { account, password, nickname } : { account, password }
    });
    if (!result.ok) {
      showAuthError('loginError', result.data.error ||
        (isRegister ? '注册失败，请更换账号后再试' : '账号或密码不正确'));
      return;
    }
    document.getElementById('loginError').hidden = true;
    currentUser = result.data.user || null;
    document.getElementById('loginAccount').value = account;
    await afterAuthenticated(currentUser);
  } catch (error) {
    showAuthError('loginError', '无法连接服务器，请确认服务已启动');
  } finally {
    submit.disabled = false;
    submit.textContent = authMode === 'register' ? '注册并登录' : '登录';
  }
});

// ---------- 忘记密码：邮箱验证码 ----------
const resetLayer = document.getElementById('resetLayer');
const resetError = document.getElementById('resetError');
let resetTimer = null;

function setResetError(text, ok) {
  resetError.textContent = text || '';
  resetError.hidden = !text;
  resetError.classList.toggle('is-ok', !!ok);
}

function openResetLayer() {
  resetLayer.hidden = false;
  setResetError('');
  const account = document.getElementById('loginAccount').value.trim();
  if (account) document.getElementById('resetAccount').value = account;
  document.getElementById('resetCode').value = '';
  document.getElementById('resetPassword').value = '';
  if (!account) document.getElementById('resetAccount').focus();
}

function closeResetLayer() {
  resetLayer.hidden = true;
  if (resetTimer) { clearInterval(resetTimer); resetTimer = null; }
  const send = document.getElementById('resetSendCode');
  send.disabled = false;
  send.textContent = '发送验证码';
}

function startResetCountdown(seconds) {
  const send = document.getElementById('resetSendCode');
  let left = seconds;
  send.disabled = true;
  send.textContent = left + 's 后重发';
  if (resetTimer) clearInterval(resetTimer);
  resetTimer = setInterval(function () {
    left -= 1;
    if (left <= 0) {
      clearInterval(resetTimer);
      resetTimer = null;
      send.disabled = false;
      send.textContent = '重新发送';
      return;
    }
    send.textContent = left + 's 后重发';
  }, 1000);
}

document.getElementById('forgotBtn').addEventListener('click', function () {
  openResetLayer();
});

// 整行也可点击：手机上文字按钮较小，扩大可点区域
const forgotRow = document.querySelector('.login-forgot-row');
if (forgotRow) {
  forgotRow.addEventListener('click', function () {
    openResetLayer();
  });
}

document.getElementById('resetCancel').addEventListener('click', closeResetLayer);

document.getElementById('resetSendCode').addEventListener('click', async function () {
  const account = document.getElementById('resetAccount').value.trim();
  if (!account) { setResetError('请先输入账号'); return; }
  const send = document.getElementById('resetSendCode');
  send.disabled = true;
  send.textContent = '发送中…';
  setResetError('');
  try {
    const result = await api('/api/auth/forgot', { method: 'POST', body: { account } });
    if (!result.ok) {
      send.disabled = false;
      send.textContent = '发送验证码';
      setResetError(result.data.error || '验证码发送失败，请稍后再试');
      return;
    }
    setResetError('验证码已发送至 ' + (result.data.email || '绑定邮箱') +
      '，10 分钟内有效', true);
    startResetCountdown(60);
    document.getElementById('resetCode').focus();
  } catch (error) {
    send.disabled = false;
    send.textContent = '发送验证码';
    setResetError('无法连接服务器，请检查网络');
  }
});

document.getElementById('resetSubmit').addEventListener('click', async function () {
  const account = document.getElementById('resetAccount').value.trim();
  const code = document.getElementById('resetCode').value.replace(/\D/g, '');
  const password = document.getElementById('resetPassword').value;
  if (!account) { setResetError('请先输入账号'); return; }
  if (code.length !== 6) { setResetError('请输入 6 位数字验证码'); return; }
  if (password.length < 6) { setResetError('新密码至少 6 位'); return; }

  const submit = document.getElementById('resetSubmit');
  submit.disabled = true;
  submit.textContent = '提交中…';
  setResetError('');
  try {
    const result = await api('/api/auth/reset', {
      method: 'POST',
      body: { account, code, newPassword: password }
    });
    if (!result.ok) {
      setResetError(result.data.error || '重置失败，请稍后再试');
      return;
    }
    closeResetLayer();
    document.getElementById('loginAccount').value = account;
    document.getElementById('loginPassword').value = '';
    const notice = document.getElementById('loginNotice');
    notice.textContent = '密码已重置，请用新密码登录';
    notice.hidden = false;
    document.getElementById('loginPassword').focus();
  } catch (error) {
    setResetError('无法连接服务器，请检查网络');
  } finally {
    submit.disabled = false;
    submit.textContent = '重置密码';
  }
});

// 页面打开时聚焦账号输入框
window.addEventListener('load', function () {
  document.getElementById('loginAccount').focus();
});

// 标签式多选（健康状况、忌口）
document.querySelectorAll('.pref-chips').forEach(function (group) {
  group.addEventListener('click', function (event) {
    const chip = event.target.closest('.pref-chip');
    if (!chip) return;

    const noneChip = group.querySelector('.pref-chip[data-value="无"]');

    if (chip.dataset.value === '无') {
      group.querySelectorAll('.pref-chip').forEach(function (item) {
        item.classList.remove('selected');
      });
      chip.classList.add('selected');
      return;
    }

    if (noneChip) noneChip.classList.remove('selected');
    chip.classList.toggle('selected');

    // 一个都没选时，自动回到「无」
    if (!group.querySelector('.pref-chip.selected') && noneChip) {
      noneChip.classList.add('selected');
    }
  });
});

function getChipValues(groupId) {
  return Array.from(document.querySelectorAll('#' + groupId + ' .pref-chip.selected'))
    .map(function (chip) { return chip.dataset.value; })
    .filter(function (value) { return value !== '无'; });
}

// 手动录入自定义健康情况 / 忌口
document.querySelectorAll('.pref-custom-input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter') return;
    event.preventDefault();

    const value = input.value.trim();
    if (!value) return;

    const group = document.getElementById(input.dataset.group);
    const exists = Array.from(group.querySelectorAll('.pref-chip')).some(function (chip) {
      return chip.dataset.value === value;
    });
    if (exists) {
      showToast('这个选项已经存在');
      input.value = '';
      return;
    }

    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'pref-chip selected';
    chip.dataset.value = value;
    chip.textContent = value;
    group.appendChild(chip);

    const noneChip = group.querySelector('.pref-chip[data-value="无"]');
    if (noneChip) noneChip.classList.remove('selected');

    input.value = '';
    showToast('已添加：' + value);
  });
});

function enterApp() {
  loginView.hidden = true;
  onboardingView.hidden = true;
  appShell.hidden = false;
  window.scrollTo(0, 0);
}

// ---------- 侧边栏：修改基本信息（复用注册问卷） ----------
let editingBasic = false;

function setSelectValue(id, value) {
  const select = document.getElementById(id);
  if (!select || value === undefined || value === null || value === '') return;
  const target = String(value);
  const exists = Array.from(select.options).some(function (option) {
    return option.value === target || option.textContent === target;
  });
  if (exists) select.value = target;
}

function setChipValues(groupId, values) {
  const group = document.getElementById(groupId);
  if (!group) return;
  const list = Array.isArray(values) ? values : [];
  if (!list.length) {
    const none = group.querySelector('.pref-chip[data-value="无"]');
    if (none) {
      group.querySelectorAll('.pref-chip').forEach(function (chip) {
        chip.classList.toggle('selected', chip === none);
      });
    }
    return;
  }
  group.querySelectorAll('.pref-chip').forEach(function (chip) {
    chip.classList.toggle('selected', list.indexOf(chip.dataset.value) !== -1);
  });
}

function prefillOnboarding() {
  const profile = readProfile();
  const preferences = loadData('preferences', {}) || {};

  document.getElementById('obName').value = profile.nickname || '';
  document.getElementById('obEmail').value = profile.email || '';
  setSelectValue('obGender', profile.gender || '女');
  document.getElementById('obAge').value = preferences.age || '';
  document.getElementById('obHeight').value = profile.height || '';
  document.getElementById('obWeight').value = profile.weight || '';
  setSelectValue('obSleep', preferences.sleepQuality || '一般');
  setSelectValue('obExercise', preferences.exerciseFrequency || '每周 1-2 次');
  setSelectValue('obGoal', preferences.goal || '减脂塑形');
  setSelectValue('obTaste', preferences.taste || '清淡');
  setSelectValue('obDietType', preferences.dietType || '均衡饮食');
  setSelectValue('obMeals', preferences.meals || '3 餐');
  setChipValues('obConditions', preferences.conditions || []);
  setChipValues('obRestrictions', preferences.restrictions || []);
  document.querySelectorAll('.pref-custom-input').forEach(function (input) {
    input.value = '';
  });
}

document.getElementById('editBasicBtn').addEventListener('click', function () {
  editingBasic = true;
  prefillOnboarding();
  loginView.hidden = true;
  appShell.hidden = true;
  onboardingView.hidden = false;
  window.scrollTo(0, 0);
});

// 跳过填写 / 取消编辑，直接进入系统
document.getElementById('skipOnboarding').addEventListener('click', function () {
  editingBasic = false;
  enterApp();
});

// 保存基本信息、健康情况与饮食偏好
document.getElementById('onboardingForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const name = document.getElementById('obName').value.trim() ||
    (currentUser && (currentUser.nickname || currentUser.account)) || '';
  const email = document.getElementById('obEmail').value.trim();
  const gender = document.getElementById('obGender').value;
  const height = parseFloat(document.getElementById('obHeight').value);
  const weight = parseFloat(document.getElementById('obWeight').value);
  const goal = document.getElementById('obGoal').value;
  const taste = document.getElementById('obTaste').value;
  const dietType = document.getElementById('obDietType').value;
  const restrictions = getChipValues('obRestrictions');

  // 同步到侧边栏
  document.getElementById('sideUserName').textContent = name || '健康用户';
  document.getElementById('sideUserSub').textContent =
    gender + ' · ' + (height > 0 ? height + 'cm' : '未填写身高');

  // 同步到个人信息弹窗（昵称用于展示，姓名选填）
  document.getElementById('pNickname').value = name;
  document.getElementById('pName').value = '';
  document.getElementById('pGender').value = gender;
  if (height > 0) document.getElementById('pHeight').value = height;
  if (weight > 0) document.getElementById('pWeight').value = weight.toFixed(1);

  // 保存档案，再次打开系统时沿用昵称、头像与基础信息
  saveData('profile', {
    nickname: name,
    name: '',
    avatar: currentAvatar,
    avatarImage: customAvatarImage,
    gender: gender,
    height: height > 0 ? height : 0,
    weight: weight > 0 ? weight : 0,
    email: email
  });

  // 邮箱同步到服务器，忘记密码时用来接收验证码
  if (serverMode && email) {
    api('/api/profile', { method: 'PUT', body: { email: email } }).then(function (result) {
      if (!result.ok) showToast(result.data.error || '邮箱保存失败');
    }).catch(function () {
      showToast('邮箱保存失败，请检查网络');
    });
  }

  // 健康情况与饮食偏好单独存档，用于饮食建议与后续个性化
  const previousPreferences = loadData('preferences', {}) || {};
  const ageValue = parseFloat(document.getElementById('obAge').value);
  saveData('preferences', {
    age: ageValue > 0 ? ageValue : (previousPreferences.age || ''),
    sleepQuality: document.getElementById('obSleep').value,
    exerciseFrequency: document.getElementById('obExercise').value,
    goal: goal,
    conditions: getChipValues('obConditions'),
    taste: taste,
    dietType: dietType,
    restrictions: restrictions,
    meals: document.getElementById('obMeals').value
  });

  // 同步到核心体征并重算 BMI
  if (weight > 0) {
    document.getElementById('weightValue').textContent = weight.toFixed(1);
  }
  if (height > 0 && weight > 0) {
    setBmiDisplay(weight / Math.pow(height / 100, 2));
  }

  // 性别联动女性健康档案
  currentGender = gender;
  applyGenderView();

  // 健康目标联动「科学变美」计划类型
  const beautyType = document.getElementById('beautyType');
  if (goal === '增肌紧致') {
    beautyType.value = '增肌塑形';
  } else if (goal === '改善体态') {
    beautyType.value = '体态改善';
  } else {
    beautyType.value = '健身减脂';
  }

  // 饮食偏好联动饮食建议
  document.getElementById('dietTipText').textContent =
    '根据你的' + taste + '口味与' + dietType + '偏好' +
    (restrictions.length ? '（忌口：' + restrictions.join('、') + '）' : '') +
    '，建议三餐规律、优先选择天然食材，并保证每日蛋白质摄入。';

  editingBasic = false;
  enterApp();
  renderVitalRanges();
  loadProfileView();
  refreshDietViews();
  applyGenderView();
  showToast('健康档案已保存');
});

/* ==========================================================
   一、顶部导航：切换六个页面
   ========================================================== */
const navButtons = Array.from(document.querySelectorAll('#nav button'));
const pages = Array.from(document.querySelectorAll('.page'));

// 空状态里的引导按钮：跳转页面 / 聚焦输入框
document.addEventListener('click', function (event) {
  const goto = event.target.closest('[data-goto]');
  if (goto) {
    switchPage(goto.getAttribute('data-goto'));
    return;
  }
  const focus = event.target.closest('[data-focus]');
  if (focus) {
    const el = document.getElementById(focus.getAttribute('data-focus'));
    if (el) el.focus();
  }
});

document.getElementById('vitalsTipBtn').addEventListener('click', openProfile);

function switchPage(name) {
  // 数据大屏仅管理员可进入，普通用户即使触发也直接忽略
  if (name === 'admin' && !(serverMode && currentUser && currentUser.role === 'admin')) {
    return;
  }
  // 高亮当前导航
  navButtons.forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.page === name);
  });
  // 显示对应页面（其余隐藏）
  pages.forEach(function (page) {
    page.classList.toggle('active', page.id === 'page-' + name);
  });
  // AI 解读页隐藏通用 Hero，首屏只保留上传区
  const mainArea = document.querySelector('.main-area');
  // 数据大屏只给管理员看，打开时刷新一次，之后每 20 秒自动更新
  if (name === 'admin') {
    loadAdminDashboard();
    if (!adminTimer) adminTimer = setInterval(loadAdminDashboard, 20000);
  } else if (adminTimer) {
    clearInterval(adminTimer);
    adminTimer = null;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

navButtons.forEach(function (btn) {
  btn.addEventListener('click', function () {
    switchPage(btn.dataset.page);
  });
});

/* ==========================================================
   管理员数据大屏：把终端里刷的运行信息画成图
   ========================================================== */
let adminTimer = null;
const adminCharts = {};

// 只有 admin 账号能看到入口，普通用户完全不可见
function updateAdminEntry() {
  const btn = document.getElementById('navAdmin');
  if (!btn) return;
  const allowed = !!(serverMode && currentUser && currentUser.role === 'admin');
  btn.hidden = !allowed;
  const adminPage = document.getElementById('page-admin');
  if (adminPage) adminPage.hidden = !allowed;
  if (!allowed && adminPage && adminPage.classList.contains('active')) {
    switchPage('data');
  }
}

function ensureECharts() {
  if (window.echarts) return Promise.resolve(true);
  if (window.__hmEChartsLoading) return window.__hmEChartsLoading;
  window.__hmEChartsLoading = new Promise(function (resolve) {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js';
    script.onload = function () { resolve(true); };
    script.onerror = function () { resolve(false); };
    document.head.appendChild(script);
  });
  return window.__hmEChartsLoading;
}

const ADMIN_CHART_TEXT = { color: '#5e6c58', fontSize: 11 };

function adminBaseOption(extra) {
  return Object.assign({
    grid: { left: 40, right: 16, top: 26, bottom: 28 },
    tooltip: { trigger: 'axis' },
    textStyle: ADMIN_CHART_TEXT
  }, extra);
}

function drawAdminChart(id, option) {
  const box = document.getElementById(id);
  if (!box || !window.echarts) return;
  if (!adminCharts[id]) adminCharts[id] = window.echarts.init(box);
  adminCharts[id].setOption(option, true);
}

function renderAdminKpis(d) {
  const items = [
    { label: '注册账号', value: d.users, note: '今日新增 ' + d.usersToday + ' 个 · 在线 ' + d.online + ' 个' },
    { label: '本次运行', value: Math.floor(d.uptime / 3600) + ' 小时', note: '服务启动至今' },
    { label: '接口请求', value: d.requests24h, note: '平均 ' + d.avgMs + ' ms · 报错 ' + d.errors24h + ' 次' },
    { label: '模型调用', value: d.aiCalls, note: '成功率 ' + d.aiOkRate + '% · 平均 ' + d.aiAvgMs + ' ms' },
    { label: '饮食记录', value: d.meals, note: '累计条数' },
    { label: '体重记录', value: d.weights, note: '累计条数' },
    { label: '运动记录', value: d.sports, note: '累计天数' },
    { label: 'AI 对话', value: d.aiMessages, note: '累计消息数' }
  ];
  document.getElementById('adminKpis').innerHTML = items.map(function (item) {
    return '<div class="admin-kpi"><span>' + item.label + '</span><b>' + item.value +
      '</b><em>' + item.note + '</em></div>';
  }).join('');
}

function renderAdminLogs(logs) {
  const box = document.getElementById('adminLogs');
  if (!logs.length) {
    box.innerHTML = '<div class="admin-log-row"><span class="admin-log-text">' +
      '暂无日志，操作一下页面再刷新。</span></div>';
    return;
  }
  box.innerHTML = logs.slice().reverse().map(function (log) {
    return '<div class="admin-log-row"><span class="admin-log-time">' +
      escapeNewsHtml(log.time) + '</span><span class="admin-log-level ' + log.level + '">' +
      log.level + '</span><span class="admin-log-text">' + escapeNewsHtml(log.text) + '</span></div>';
  }).join('');
}

function renderAdminCharts(d) {
  if (!window.echarts) return;

  drawAdminChart('adminChartRequests', adminBaseOption({
    xAxis: {
      type: 'category', data: d.hours,
      axisLine: { lineStyle: { color: '#e1e8dc' } }, axisLabel: ADMIN_CHART_TEXT
    },
    yAxis: {
      type: 'value', minInterval: 1,
      splitLine: { lineStyle: { color: '#f3ece3' } }, axisLabel: ADMIN_CHART_TEXT
    },
    series: [{
      type: 'bar', data: d.hourRequests, barWidth: 12,
      itemStyle: { color: '#c98a5a', borderRadius: [4, 4, 0, 0] }
    }]
  }));

  drawAdminChart('adminChartErrors', adminBaseOption({
    xAxis: {
      type: 'category', data: d.hours,
      axisLine: { lineStyle: { color: '#e1e8dc' } }, axisLabel: ADMIN_CHART_TEXT
    },
    yAxis: {
      type: 'value', minInterval: 1,
      splitLine: { lineStyle: { color: '#f3ece3' } }, axisLabel: ADMIN_CHART_TEXT
    },
    series: [{
      type: 'line', data: d.hourErrors, smooth: true, symbolSize: 6,
      lineStyle: { color: '#d24b4b', width: 2 },
      itemStyle: { color: '#d24b4b' },
      areaStyle: { color: 'rgba(210, 75, 75, 0.10)' }
    }]
  }));

  const aiSeries = d.aiSeries || [];
  drawAdminChart('adminChartAi', adminBaseOption({
    xAxis: {
      type: 'category', data: aiSeries.map(function (item) { return item.time.slice(6); }),
      axisLine: { lineStyle: { color: '#e1e8dc' } }, axisLabel: ADMIN_CHART_TEXT
    },
    yAxis: {
      type: 'value', name: 'ms',
      splitLine: { lineStyle: { color: '#f3ece3' } }, axisLabel: ADMIN_CHART_TEXT
    },
    series: [{
      type: 'line', smooth: true, symbolSize: 6,
      data: aiSeries.map(function (item) {
        return {
          value: item.ms,
          itemStyle: { color: item.ok ? '#5d9c43' : '#d24b4b' }
        };
      }),
      lineStyle: { color: '#455c3d', width: 2 }
    }]
  }));

  drawAdminChart('adminChartData', {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: ADMIN_CHART_TEXT },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { color: '#6b5a4a', fontSize: 11 },
      data: [
        { name: '饮食', value: d.meals },
        { name: '体重', value: d.weights },
        { name: '运动', value: d.sports },
        { name: '睡眠', value: d.sleeps },
        { name: '心情', value: d.moods },
        { name: '报告', value: d.reports }
      ]
    }]
  });
}

async function loadAdminDashboard() {
  if (!serverMode || !currentUser) return;

  const libReady = await ensureECharts();
  const result = await api('/api/admin/overview');
  if (!result.ok) {
    showToast((result.data && result.data.error) || '数据大屏加载失败');
    return;
  }

  const d = result.data;
  renderAdminKpis(d);
  renderAdminLogs(d.logs || []);
  if (libReady) renderAdminCharts(d);
}

const adminRefreshBtn = document.getElementById('adminRefresh');
if (adminRefreshBtn) adminRefreshBtn.addEventListener('click', loadAdminDashboard);

window.addEventListener('resize', function () {
  Object.keys(adminCharts).forEach(function (id) {
    adminCharts[id].resize();
  });
});

/* ==========================================================
   二、轻提示 Toast
   ========================================================== */
let toastTimer = null;

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () {
    toast.classList.remove('show');
  }, 2200);
}

// 所有带 data-toast 的按钮，点击后弹出对应提示
document.querySelectorAll('[data-toast]').forEach(function (el) {
  el.addEventListener('click', function () {
    showToast(el.dataset.toast);
  });
});

/* ==========================================================
   三、个人信息档案弹窗
   ========================================================== */
const profileMask = document.getElementById('profileMask');

/* ---------- 头像预设：用户可自由选择 ---------- */
const avatarPresets = [
  { emoji: '🌿', bg: 'linear-gradient(135deg, #8fd9b6, #4ecdc4)' },
  { emoji: '🌻', bg: 'linear-gradient(135deg, #ffd36e, #f5a623)' },
  { emoji: '🍑', bg: 'linear-gradient(135deg, #ffb3b3, #ff7a8a)' },
  { emoji: '🐱', bg: 'linear-gradient(135deg, #a8c8f0, #7aa6e8)' },
  { emoji: '🐼', bg: 'linear-gradient(135deg, #c9d6e3, #8fa6bd)' },
  { emoji: '🦊', bg: 'linear-gradient(135deg, #ffbe8a, #f08a4b)' },
  { emoji: '🐳', bg: 'linear-gradient(135deg, #8fd3f4, #5aa9e6)' },
  { emoji: '🌙', bg: 'linear-gradient(135deg, #b6a7f0, #8a6cf0)' },
  { emoji: '☀️', bg: 'linear-gradient(135deg, #ffe08a, #ffb74d)' },
  { emoji: '🍀', bg: 'linear-gradient(135deg, #9be89b, #5cc46a)' }
];

let currentAvatar = 0;
let customAvatarImage = null; // 用户上传并裁剪后的头像（dataURL）

function readProfile() {
  const saved = loadData('profile', null);
  return saved && typeof saved === 'object' ? saved : {};
}

// 侧边栏头像：优先显示用户上传的头像，否则使用预设表情
function renderSideAvatar() {
  const avatar = document.getElementById('sideAvatar');
  if (customAvatarImage) {
    avatar.innerHTML = '<img src="' + customAvatarImage + '" alt="我的头像">';
    avatar.style.background = '#f4f1ec';
    return;
  }
  const preset = avatarPresets[currentAvatar] || avatarPresets[0];
  avatar.textContent = preset.emoji;
  avatar.style.background = preset.bg;
}

function updateAvatarSelection() {
  document.querySelectorAll('.avatar-option').forEach(function (btn) {
    const isUpload = btn.classList.contains('avatar-upload');
    btn.classList.toggle('selected', isUpload
      ? !!customAvatarImage
      : !customAvatarImage && Number(btn.dataset.avatar) === currentAvatar);

    if (isUpload) {
      btn.innerHTML = customAvatarImage
        ? '<img src="' + customAvatarImage + '" alt="自定义头像">'
        : '＋';
    }
  });
}

// 选择预设头像：会清除已上传的自定义头像
function applyAvatar(index) {
  const safe = (index >= 0 && index < avatarPresets.length) ? index : 0;
  currentAvatar = safe;
  customAvatarImage = null;
  renderSideAvatar();
  updateAvatarSelection();
}

function renderAvatarPicker() {
  const picker = document.getElementById('avatarPicker');
  picker.innerHTML = '';
  avatarPresets.forEach(function (preset, index) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'avatar-option';
    btn.dataset.avatar = index;
    btn.style.background = preset.bg;
    btn.textContent = preset.emoji;
    btn.title = '头像 ' + (index + 1);
    btn.addEventListener('click', function () {
      applyAvatar(index);
    });
    picker.appendChild(btn);
  });

  // 最后一个：上传自定义头像
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'avatar-option avatar-upload';
  uploadBtn.title = '上传头像';
  uploadBtn.addEventListener('click', function () {
    document.getElementById('avatarUploadInput').click();
  });
  picker.appendChild(uploadBtn);
}

// 页面加载：回显已保存的昵称、姓名、头像与体重
function loadProfileView() {
  const profile = readProfile();
  const nickname = profile.nickname ||
    (currentUser && (currentUser.nickname || currentUser.account)) || '健康用户';

  document.getElementById('sideUserName').textContent = nickname;
  if (profile.gender) {
    document.getElementById('sideUserSub').textContent =
      profile.gender + ' · ' + (profile.height ? profile.height + 'cm' : '未填写身高');
  }

  currentAvatar = typeof profile.avatar === 'number' ? profile.avatar : 0;
  customAvatarImage = profile.avatarImage || null;

  renderAvatarPicker();
  renderSideAvatar();
  updateAvatarSelection();

  // 恢复体重与 BMI：与变美计划、营养目标使用同一个体重来源，避免一处有值一处显示「—」
  const restoredWeight = getCurrentWeight();
  if (restoredWeight > 0) {
    document.getElementById('weightValue').textContent = restoredWeight.toFixed(1);
    const restoredHeight = currentHeightCm();
    setBmiDisplay(restoredHeight > 0
      ? restoredWeight / Math.pow(restoredHeight / 100, 2)
      : 0);
  } else {
    document.getElementById('weightValue').textContent = '—';
    setBmiDisplay(0);
  }

  // 体重 / 身高变化后同步正常值范围与异常提醒
  renderVitalRanges();
}

function openProfile() {
  const profile = readProfile();
  // 打开弹窗时回显当前资料
  document.getElementById('pAccount').value = (currentUser && currentUser.account) || '';
  document.getElementById('pEmail').value = profile.email || '';
  document.getElementById('pNickname').value = profile.nickname || '';
  document.getElementById('pName').value = profile.name || '';
  document.getElementById('pGender').value = currentGender;
  if (profile.height) document.getElementById('pHeight').value = profile.height;
  if (profile.weight) document.getElementById('pWeight').value = profile.weight.toFixed(1);
  currentAvatar = typeof profile.avatar === 'number' ? profile.avatar : currentAvatar;
  customAvatarImage = profile.avatarImage || null;
  renderAvatarPicker();
  renderSideAvatar();
  updateAvatarSelection();
  profileMask.classList.add('open');
  document.body.style.overflow = 'hidden'; // 弹窗打开时禁止页面滚动
}

function closeProfile() {
  profileMask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

document.getElementById('userBtn').addEventListener('click', openProfile);
document.getElementById('profileClose').addEventListener('click', closeProfile);

// 点击遮罩空白处也能关闭
profileMask.addEventListener('click', function (event) {
  if (event.target === profileMask) closeProfile();
});

// 保存档案：同步更新「健康数据」中的体重与 BMI
document.getElementById('saveProfile').addEventListener('click', function () {
  const nickname = document.getElementById('pNickname').value.trim() || '健康用户';
  const name = document.getElementById('pName').value.trim(); // 姓名选填，允许为空
  const email = document.getElementById('pEmail').value.trim(); // QQ 邮箱，用于找回密码
  const gender = document.getElementById('pGender').value;
  const height = parseFloat(document.getElementById('pHeight').value);
  const weight = parseFloat(document.getElementById('pWeight').value);

  if (!height || !weight || height <= 0 || weight <= 0) {
    showToast('请填写正确身高和体重');
    return;
  }

  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    showToast('QQ 邮箱格式不对，例如 12345678@qq.com');
    return;
  }

  // 体重
  document.getElementById('weightValue').textContent = weight.toFixed(1);
  addWeightRecord(weight);

  // BMI = 体重(kg) / 身高(m) 的平方
  const bmi = weight / Math.pow(height / 100, 2);
  setBmiDisplay(bmi);

  // 昵称用于展示，姓名仅在填写后写入档案
  document.getElementById('userBtn').title = '个人信息 · ' + nickname + '（' + gender + '）';
  document.getElementById('sideUserName').textContent = nickname;
  document.getElementById('sideUserSub').textContent = gender + ' · ' + height + 'cm';

  // 头像、昵称、姓名等一并存入本地，刷新后仍然保留
  saveData('profile', {
    nickname: nickname,
    name: name,
    avatar: currentAvatar,
    avatarImage: customAvatarImage,
    gender: gender,
    height: height,
    weight: weight,
    email: email
  });

  // 邮箱同步到服务器，忘记密码时用它接收验证码
  if (serverMode) {
    api('/api/profile', { method: 'PUT', body: { email: email } }).then(function (result) {
      if (!result.ok) showToast(result.data.error || '邮箱保存失败');
    }).catch(function () {
      showToast('邮箱保存失败，请检查网络');
    });
  }

  // 根据性别显示/隐藏「健康数据」页中的女性健康档案
  currentGender = gender;
  applyGenderView();

  // 营养目标与体重相关，档案变化后重新计算
  refreshDietViews();

  // 身高或体重变化后同步正常值范围、异常提醒与 BMI 公式
  renderVitalRanges();

  closeProfile();
  showToast(name ? '个人信息已保存' : '个人信息已保存（姓名可稍后补充）');
});

/* ---------- 头像上传与裁剪 ---------- */
const cropMask = document.getElementById('cropMask');
const cropStage = document.getElementById('cropStage');
const cropImg = document.getElementById('cropImage');
const cropZoom = document.getElementById('cropZoom');
const CROP_SIZE = 240;

let cropSource = null;
let cropBaseScale = 1;
let cropScale = 1;
let cropOffsetX = 0;
let cropOffsetY = 0;
let cropDragging = false;
let cropPointerStart = { x: 0, y: 0, ox: 0, oy: 0 };

function cropDisplaySize() {
  return {
    w: cropSource.naturalWidth * cropBaseScale * cropScale,
    h: cropSource.naturalHeight * cropBaseScale * cropScale
  };
}

// 图片始终铺满裁剪框，并限制拖动范围，避免出现空白边缘
function layoutCropImage() {
  if (!cropSource) return;
  const size = cropDisplaySize();
  const maxX = Math.max(0, (size.w - CROP_SIZE) / 2);
  const maxY = Math.max(0, (size.h - CROP_SIZE) / 2);
  cropOffsetX = Math.min(maxX, Math.max(-maxX, cropOffsetX));
  cropOffsetY = Math.min(maxY, Math.max(-maxY, cropOffsetY));

  cropImg.style.width = size.w + 'px';
  cropImg.style.height = size.h + 'px';
  cropImg.style.marginLeft = cropOffsetX + 'px';
  cropImg.style.marginTop = cropOffsetY + 'px';
}

function closeCrop() {
  cropMask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

document.getElementById('avatarUploadInput').addEventListener('change', function () {
  const file = this.files && this.files[0];
  this.value = ''; // 允许连续选择同一张图片
  if (!file) return;
  if (file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  const reader = new FileReader();
  reader.onload = function () {
    const image = new Image();
    image.onload = function () {
      cropSource = image;
      cropBaseScale = Math.max(CROP_SIZE / image.naturalWidth, CROP_SIZE / image.naturalHeight);
      cropScale = 1;
      cropZoom.value = 100;
      cropOffsetX = 0;
      cropOffsetY = 0;
      cropImg.src = image.src;
      layoutCropImage();
      cropMask.classList.add('open');
      document.body.style.overflow = 'hidden';
    };
    image.onerror = function () {
      showToast('图片加载失败，请换一张试试');
    };
    image.src = reader.result;
  };
  reader.onerror = function () {
    showToast('图片读取失败，请重试');
  };
  reader.readAsDataURL(file);
});

cropStage.addEventListener('pointerdown', function (event) {
  if (!cropSource) return;
  cropDragging = true;
  cropStage.classList.add('dragging');
  cropStage.setPointerCapture(event.pointerId);
  cropPointerStart = {
    x: event.clientX,
    y: event.clientY,
    ox: cropOffsetX,
    oy: cropOffsetY
  };
});

cropStage.addEventListener('pointermove', function (event) {
  if (!cropDragging) return;
  cropOffsetX = cropPointerStart.ox + (event.clientX - cropPointerStart.x);
  cropOffsetY = cropPointerStart.oy + (event.clientY - cropPointerStart.y);
  layoutCropImage();
});

function endCropDrag() {
  cropDragging = false;
  cropStage.classList.remove('dragging');
}

cropStage.addEventListener('pointerup', endCropDrag);
cropStage.addEventListener('pointercancel', endCropDrag);

cropZoom.addEventListener('input', function () {
  cropScale = Number(cropZoom.value) / 100;
  layoutCropImage();
});

document.getElementById('cropSave').addEventListener('click', function () {
  if (!cropSource) {
    closeCrop();
    return;
  }

  const display = cropDisplaySize();
  const left = CROP_SIZE / 2 + cropOffsetX - display.w / 2;
  const top = CROP_SIZE / 2 + cropOffsetY - display.h / 2;
  const ratio = cropSource.naturalWidth / display.w;

  const canvas = document.createElement('canvas');
  canvas.width = CROP_SIZE;
  canvas.height = CROP_SIZE;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, CROP_SIZE, CROP_SIZE);
  ctx.drawImage(
    cropSource,
    -left * ratio, -top * ratio, CROP_SIZE * ratio, CROP_SIZE * ratio,
    0, 0, CROP_SIZE, CROP_SIZE
  );

  customAvatarImage = canvas.toDataURL('image/jpeg', 0.88);
  renderSideAvatar();
  updateAvatarSelection();
  closeCrop();
  showToast('头像已更新，记得点击「保存修改」');
});

document.getElementById('cropClose').addEventListener('click', closeCrop);
document.getElementById('cropCancel').addEventListener('click', closeCrop);
cropMask.addEventListener('click', function (event) {
  if (event.target === cropMask) closeCrop();
});

/* ==========================================================
   四、饮食记录：输入框回车即可记录
   ========================================================== */
document.querySelectorAll('.meal input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.keyCode !== 13) return;
    // 中文输入法选词时的回车不算提交，避免把未上屏的拼音当成食物
    if (event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    requestMealRecord(input.dataset.meal, input.value, input);
  });
});

// 点「记录」按钮同样可以提交，避免部分输入法 / 移动端回车无效
document.querySelectorAll('.meal-btn').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const input = btn.parentElement.querySelector('input');
    if (!input) return;
    requestMealRecord(input.dataset.meal, input.value, input);
  });
});

/* ==========================================================
   四之二、图片上传
   说明：图片上传到后端 /api/uploads 并随记录一起存档；
        识别结果仍为示例数据，接入豆包视觉模型 / OCR 后可替换。
   ========================================================== */

// 上传前先把图片压小：手机原图常有 3–10MB，压缩后约 150KB，
// 上传更快、模型读取也更稳，还能顺带把 iPhone 的 HEIC 转成 JPEG
function compressImageFile(file, maxSide, quality) {
  return new Promise(function (resolve) {
    if (!file || !file.type || file.type.indexOf('image/') !== 0) {
      resolve(file);
      return;
    }
    const reader = new FileReader();
    reader.onerror = function () { resolve(file); };
    reader.onload = function () {
      const image = new Image();
      image.onerror = function () { resolve(file); };
      image.onload = function () {
        const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
        if (scale >= 1 && file.size < 400 * 1024) {
          resolve(file);
          return;
        }
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        const context = canvas.getContext('2d');
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (blob) {
          if (!blob) { resolve(file); return; }
          const name = (file.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg';
          resolve(new File([blob], name, { type: 'image/jpeg' }));
        }, 'image/jpeg', quality);
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

// 上传图片到后端，返回可访问的图片地址；静态演示模式不落库，返回 null
async function uploadImage(file) {
  if (!serverMode) return null;
  const prepared = await compressImageFile(file, 1280, 0.82);
  const headers = {
    'Content-Type': prepared.type || 'application/octet-stream',
    'X-File-Name': encodeURIComponent(prepared.name || 'upload')
  };
  return fetch('/api/uploads', {
    method: 'POST',
    credentials: 'same-origin',
    headers: headers,
    body: prepared
  }).then(function (response) {
    return response.json().then(function (data) {
      if (!response.ok || !data.file || !data.file.url) {
        throw new Error(data.error || '图片上传失败');
      }
      return data.file.url;
    });
  });
}

// ---------- 餐食图片上传 ----------
const dietImageInput = document.getElementById('dietImageInput');
const dietPreview = document.getElementById('dietPreview');
const dietUploadEmpty = document.getElementById('dietUploadEmpty');
const dietPreviewImg = document.getElementById('dietPreviewImg');
const dietFileName = document.getElementById('dietFileName');
const dietStatus = document.getElementById('dietStatus');

// 识别期间禁用「选择图片」并给出即时反馈
function setDietBusy(busy) {
  const btn = document.getElementById('dietChooseBtn');
  if (!btn) return;
  btn.disabled = busy;
  btn.setAttribute('aria-busy', busy ? 'true' : 'false');
  btn.textContent = busy ? '识别中…' : '选择图片';
}
const dietResult = document.getElementById('dietResult');
const dietFillMeal = document.getElementById('dietFillMeal');
const dietMealRow = document.getElementById('dietMealRow');
const dietMealType = document.getElementById('dietMealType');

let dietImageUrl = null;        // 本地预览地址
let pendingMealImage = '';      // 待写入下一条饮食记录的图片地址
let mealRecognition = null;     // 最近一次识别出的食物与营养

function chooseDietImage() {
  dietImageInput.value = '';
  dietImageInput.click();
}

document.getElementById('dietChooseBtn').addEventListener('click', chooseDietImage);
document.getElementById('dietReselect').addEventListener('click', chooseDietImage);

// 点击空白上传区也能选择图片
dietUploadEmpty.addEventListener('click', function (event) {
  if (event.target.tagName !== 'BUTTON') chooseDietImage();
});

// 按当前时间推测该记录到哪一餐
function defaultMealType() {
  const hour = new Date().getHours();
  if (hour < 10) return '早餐';
  if (hour < 15) return '午餐';
  if (hour < 21) return '晚餐';
  return '加餐';
}

function nutritionNumber(value, digits) {
  const number = Number(value);
  const safe = isFinite(number) ? number : 0;
  return digits ? Math.round(safe * 10) / 10 : Math.round(safe);
}

// 渲染识别出的食物清单、合计营养与说明
function renderMealRecognition(result) {
  mealRecognition = result || null;
  const foods = (result && result.foods) || [];
  const total = (result && result.total) || {};

  if (!foods.length) {
    dietResult.innerHTML = '<div>没有识别出明确的食物，可以换一张更清晰的照片，或在下方手动记录。</div>';
    dietResult.hidden = false;
    dietMealRow.hidden = true;
    dietFillMeal.hidden = true;
    return;
  }

  const rows = foods.map(function (item) {
    return '<div class="ai-food"><span>' + escapeHtml(item.name) +
      (item.portion ? ' · ' + escapeHtml(item.portion) : '') + '</span><b>' +
      nutritionNumber(item.kcal) + ' kcal</b></div>';
  }).join('');

  const note = result.note
    ? '<div class="ai-note">' + escapeHtml(result.note) + '</div>'
    : '';

  dietResult.innerHTML =
    '<div class="ai-foods">' + rows + '</div>' +
    '<div class="ai-total">共约 ' + nutritionNumber(total.kcal) + ' kcal · 蛋白质 ' +
    nutritionNumber(total.protein, true) + 'g · 碳水 ' + nutritionNumber(total.carb, true) +
    'g · 脂肪 ' + nutritionNumber(total.fat, true) + 'g · 纤维 ' +
    nutritionNumber(total.fiber, true) + 'g</div>' + note;
  dietResult.hidden = false;
  dietMealRow.hidden = false;
  dietFillMeal.hidden = false;
}

// 调用后端多模态识别接口
async function recognizeMealImage(url) {
  dietStatus.className = 'upload-status scanning';
  dietStatus.textContent = 'AI 正在识别食物与热量...';
  mealRecognition = null;
  dietResult.hidden = true;
  dietMealRow.hidden = true;
  dietFillMeal.hidden = true;
  setDietBusy(true);

  async function askVision() {
    return api('/api/ai/vision', {
      method: 'POST',
      body: { task: 'meal', imageUrl: url }
    });
  }

  let response = null;
  try {
    response = await askVision();
    // 大模型偶尔超时或返回 5xx，自动再试一次通常就能成功
    if (!response.ok) {
      dietStatus.textContent = '第一次识别超时，正在自动重试...';
      response = await askVision();
    }
  } catch (error) {
    try {
      dietStatus.textContent = '网络有点慢，正在自动重试...';
      response = await askVision();
    } catch (again) {
      response = null;
    }
  }

  dietStatus.className = 'upload-status';

  if (!response) {
    dietStatus.textContent = '网络不太稳定，识别没能完成。图片已保存，可在下方手动记录。';
    showToast('网络不稳定，请稍后再试或手动记录');
    setDietBusy(false);
    return;
  }

  if (!response.ok) {
    const message = (response.data && response.data.error) || '图片识别失败';
    dietStatus.textContent = message + '。图片已保存，也可以直接在下方手动记录。';
    showToast(message);
    setDietBusy(false);
    return;
  }

  const result = (response.data && response.data.result) || {};
  renderMealRecognition(result);
  const left = response.data.quotaLeft;
  dietStatus.textContent = '识别完成' +
    (typeof left === 'number' ? '（今日还可识别 ' + left + ' 次）' : '') +
    '，确认餐次后点「加入今日饮食」。';
  setDietBusy(false);
}

dietImageInput.addEventListener('change', function () {
  const file = dietImageInput.files[0];
  if (!file) return;

  if (!file.type || file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  // 预览图片
  if (dietImageUrl) URL.revokeObjectURL(dietImageUrl);
  dietImageUrl = URL.createObjectURL(file);
  dietPreviewImg.src = dietImageUrl;
  dietFileName.textContent = file.name;
  dietUploadEmpty.hidden = true;
  dietPreview.hidden = false;

  mealRecognition = null;
  pendingMealImage = '';
  dietResult.hidden = true;
  dietResult.innerHTML = '';
  dietMealRow.hidden = true;
  dietFillMeal.hidden = true;
  dietMealType.value = defaultMealType();

  if (!serverMode) {
    dietStatus.className = 'upload-status';
    dietStatus.textContent = '静态演示版无法连接识别服务，请在下方手动记录饮食。';
    return;
  }

  dietStatus.className = 'upload-status scanning';
  dietStatus.textContent = '图片上传中...';

  uploadImage(file).then(function (url) {
    pendingMealImage = url || '';
    if (!url) {
      dietStatus.className = 'upload-status';
      dietStatus.textContent = '图片上传失败，暂时无法识别；可在下方手动记录。';
      return;
    }
    return recognizeMealImage(url);
  }).catch(function (error) {
    dietStatus.className = 'upload-status';
    dietStatus.textContent = '图片上传失败：' + error.message + '。仍可手动记录饮食。';
  });
});

// 把识别结果写入选定的餐次
dietFillMeal.addEventListener('click', function () {
  if (!mealRecognition || !(mealRecognition.foods || []).length) {
    showToast('没有可记录的食物');
    return;
  }

  const meal = dietMealType.value || '午餐';
  const text = mealRecognition.foods.map(function (item) {
    return item.name;
  }).join(' ');
  const total = mealRecognition.total || {};

  saveMealRecord(meal, text, {
    kcal: nutritionNumber(total.kcal),
    protein: nutritionNumber(total.protein, true),
    carb: nutritionNumber(total.carb, true),
    fat: nutritionNumber(total.fat, true),
    fiber: nutritionNumber(total.fiber, true)
  });

  dietFillMeal.hidden = true;
  dietMealRow.hidden = true;
  dietResult.innerHTML = '<div>已记录到今天的' + escapeHtml(meal) + '，可以继续上传下一张照片。</div>';
  showToast('已加入今天的' + meal + '：' + text);
});

// ---------- 体检报告图片识别 ----------
const reportImageInput = document.getElementById('reportImageInput');
const reportPreview = document.getElementById('reportPreview');
const reportUploadEmpty = document.getElementById('reportUploadEmpty');
const reportPreviewImg = document.getElementById('reportPreviewImg');
const reportFileName = document.getElementById('reportFileName');
const reportStatus = document.getElementById('reportStatus');
const reportResult = document.getElementById('reportResult');

let reportImageUrl = null;      // 本地预览地址
let reportImagePath = '';       // 已上传到后端的图片地址
let reportUploadTask = null;    // 正在上传的任务，点击同步前先等它完成

// 识别结果可能缺少某些指标，用 null 表示“报告上没有”，避免误填 0
let reportMetrics = { weight: null, fat: null, systolic: null, diastolic: null, glucose: null };
let reportMetricsDate = toISODate(new Date());

function reportNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return isFinite(number) ? number : null;
}

function reportText(value, digits) {
  return value === null ? '—' : value.toFixed(digits === undefined ? 1 : digits);
}

// 渲染识别出的报告明细与总结
function renderReportItems(items, abnormal, hasMetrics) {
  const box = document.getElementById('reportItems');
  const summary = document.getElementById('reportSummary');
  const list = (items || []).filter(function (item) {
    return item && item.name;
  });

  if (!list.length) {
    box.hidden = true;
    box.innerHTML = '';
  } else {
    box.innerHTML = list.slice(0, 60).map(function (item) {
      return '<div class="report-item-row' + (item.abnormal ? ' is-abnormal' : '') + '">' +
        '<span class="ri-name">' + escapeHtml(item.name) + '</span>' +
        '<b class="ri-value">' + escapeHtml(item.value) +
        (item.unit ? '<span class="ri-unit"> ' + escapeHtml(item.unit) + '</span>' : '') + '</b>' +
        (item.ref ? '<em class="ri-ref">参考范围 ' + escapeHtml(item.ref) + '</em>' : '') +
        '</div>';
    }).join('');
    box.hidden = false;
  }

  if (abnormal && abnormal.length) {
    summary.className = 'report-summary is-warn';
    summary.textContent = '有 ' + abnormal.length + ' 项需要留意：' + abnormal.join('；') +
      '。识别结果仅供参考，请以报告原文和医生意见为准。';
  } else if (list.length) {
    summary.className = 'report-summary';
    summary.textContent = '这些指标未见明显异常标记。识别结果仅供参考，请以报告原文和医生意见为准。';
  } else {
    summary.className = 'report-summary';
    summary.textContent = hasMetrics
      ? '已回填基础指标。识别结果仅供参考，请以报告原文和医生意见为准。'
      : '这次没有识别到可回填的指标，可以换一张更清晰的照片，或手动填写核心体征。';
  }
}

// 把一份报告指标渲染到结果卡片
function renderReportResult(record, date) {
  reportMetrics = {
    weight: reportNumber(record.weight),
    fat: reportNumber(record.fat),
    systolic: reportNumber(record.systolic),
    diastolic: reportNumber(record.diastolic),
    glucose: reportNumber(record.glucose)
  };
  reportMetricsDate = date || toISODate(new Date());

  // 报告存档里带了图片地址时，把预览区换成存档图片（刷新后也能看到）
  if (record.imageUrl) {
    reportImagePath = record.imageUrl;
    reportPreviewImg.src = record.imageUrl;
    reportFileName.textContent = '体检报告图片';
    reportUploadEmpty.hidden = true;
    reportPreview.hidden = false;
  }

  document.getElementById('reportWeight').textContent = reportText(reportMetrics.weight);
  document.getElementById('reportFat').textContent = reportText(reportMetrics.fat);
  document.getElementById('reportBp').textContent =
    reportMetrics.systolic === null || reportMetrics.diastolic === null
      ? '—'
      : Math.round(reportMetrics.systolic) + '/' + Math.round(reportMetrics.diastolic);
  document.getElementById('reportGlucose').textContent = reportText(reportMetrics.glucose);

  const reportHeightM = currentHeightMeters();
  const bmi = reportNumber(record.bmi) || (reportMetrics.weight && reportHeightM
    ? reportMetrics.weight / (reportHeightM * reportHeightM)
    : null);
  document.getElementById('reportBmi').textContent = reportText(bmi);

  const parsed = parseISODate(reportMetricsDate);
  document.getElementById('reportDateText').textContent =
    parsed ? formatYMD(parsed) : reportMetricsDate;

  renderReportItems(record.items, record.abnormal,
    reportMetrics.weight !== null || reportMetrics.systolic !== null ||
    reportMetrics.glucose !== null);
  reportResult.hidden = false;
}

// 调用后端 OCR 接口识别体检报告
async function recognizeReportImage(url) {
  reportStatus.className = 'upload-status scanning';
  reportStatus.textContent = 'AI 正在识别报告指标...';

  const response = await api('/api/ai/vision', {
    method: 'POST',
    body: { task: 'report', imageUrl: url }
  });

  reportStatus.className = 'upload-status';

  if (!response.ok) {
    const message = (response.data && response.data.error) || '识别失败';
    reportStatus.textContent = message + '。可以换一张清晰照片，或手动填写核心体征。';
    showToast(message);
    return;
  }

  const result = (response.data && response.data.result) || {};
  renderReportResult(Object.assign({ imageUrl: reportImagePath }, result),
    result.date || toISODate(new Date()));

  const found = ['weight', 'fat', 'systolic', 'diastolic', 'glucose'].filter(function (key) {
    return reportNumber(result[key]) !== null;
  }).length;
  const left = response.data.quotaLeft;
  reportStatus.textContent = '识别完成，回填 ' + found + ' 项基础指标' +
    (typeof left === 'number' ? '（今日还可识别 ' + left + ' 次）' : '') +
    '，核对后点「同步到核心体征」。';
  showToast('报告识别完成，请核对结果');
}

// 同一天的报告只保留一条，避免重复堆积
function saveReportRecord(record) {
  const list = (loadData('reports', []) || []).slice();
  const date = record.date;
  const index = list.findIndex(function (item) {
    return item.date === date;
  });
  if (index >= 0) {
    list[index] = Object.assign({}, list[index], record);
  } else {
    list.push(record);
  }
  saveData('reports', list);
}

function chooseReportImage() {
  reportImageInput.value = '';
  reportImageInput.click();
}

document.getElementById('reportChooseBtn').addEventListener('click', chooseReportImage);
document.getElementById('reportReselect').addEventListener('click', chooseReportImage);

reportUploadEmpty.addEventListener('click', function (event) {
  if (event.target.tagName !== 'BUTTON') chooseReportImage();
});

// 核心体征右上角的快捷入口
document.getElementById('quickReportUpload').addEventListener('click', function () {
  chooseReportImage();
  document.getElementById('reportCard').scrollIntoView({ behavior: 'smooth', block: 'center' });
});

reportImageInput.addEventListener('change', function () {
  const file = reportImageInput.files[0];
  if (!file) return;

  if (!file.type || file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  if (reportImageUrl) URL.revokeObjectURL(reportImageUrl);
  reportImageUrl = URL.createObjectURL(file);
  reportPreviewImg.src = reportImageUrl;
  reportFileName.textContent = file.name;
  reportUploadEmpty.hidden = true;
  reportPreview.hidden = false;

  reportResult.hidden = true;
  reportImagePath = '';

  if (!serverMode) {
    reportStatus.className = 'upload-status';
    reportStatus.textContent = '静态演示版无法调用 OCR，请在下方手动填写核心体征。';
    return;
  }

  reportStatus.className = 'upload-status scanning';
  reportStatus.textContent = '图片上传中，随后开始识别...';

  reportUploadTask = uploadImage(file).then(function (url) {
    reportImagePath = url || '';
    return reportImagePath;
  });

  reportUploadTask.then(function (url) {
    if (!url) {
      reportStatus.className = 'upload-status';
      reportStatus.textContent = '图片上传失败，无法识别；可以手动填写核心体征。';
      return;
    }
    return recognizeReportImage(url);
  }).catch(function (error) {
    reportStatus.className = 'upload-status';
    reportStatus.textContent = '图片识别失败：' + error.message + '。可以手动填写核心体征。';
  });
});

// 将识别结果同步到核心体征，并把这份报告存档
document.getElementById('applyReport').addEventListener('click', async function () {
  // 图片可能还在上传，先等上传完成再存档
  if (reportUploadTask) {
    try {
      reportImagePath = (await reportUploadTask) || '';
    } catch (error) {
      reportImagePath = '';
      showToast('报告图片上传失败：' + error.message);
    }
    reportUploadTask = null;
  }

  const hasAny = reportMetrics.weight !== null || reportMetrics.fat !== null ||
    reportMetrics.systolic !== null || reportMetrics.diastolic !== null ||
    reportMetrics.glucose !== null;
  if (!hasAny) {
    showToast('还没有可同步的指标，请先上传报告或手动填写');
    return;
  }

  if (reportMetrics.weight !== null) {
    document.getElementById('weightValue').textContent = reportMetrics.weight.toFixed(1);
    // 体检同步的体重也进入趋势记录
    addWeightRecord(reportMetrics.weight);
    // BMI 由体重和身高算出，身高未填写时不显示数值
    const reportHeightM = currentHeightMeters();
    setBmiDisplay(reportHeightM ? reportMetrics.weight / (reportHeightM * reportHeightM) : 0);
  }

  if (reportMetrics.fat !== null) {
    document.getElementById('fatValue').textContent = reportMetrics.fat.toFixed(1);
  }

  if (reportMetrics.systolic !== null && reportMetrics.diastolic !== null) {
    document.getElementById('bpValue').textContent =
      Math.round(reportMetrics.systolic) + '/' + Math.round(reportMetrics.diastolic);
    saveData('bp', { systolic: reportMetrics.systolic, diastolic: reportMetrics.diastolic });
  }

  if (reportMetrics.glucose !== null) {
    document.getElementById('glucoseValue').textContent = reportMetrics.glucose.toFixed(1);
    saveData('glucose', reportMetrics.glucose);
  }

  saveReportRecord({
    date: reportMetricsDate,
    weight: reportMetrics.weight,
    fat: reportMetrics.fat,
    systolic: reportMetrics.systolic,
    diastolic: reportMetrics.diastolic,
    glucose: reportMetrics.glucose,
    imageUrl: reportImagePath || ''
  });
  refreshDietViews();
  renderVitalRanges();

  showToast('体检指标已同步到核心体征并保存');
});


/* ==========================================================
   五、运动页：目标与数据由用户填写，完成度自动计算
   ========================================================== */
const SPORT_DEFAULT = {
  goal: { kcal: 500, steps: 8000, minutes: 60 },
  history: {}
};

let sportState = loadData('sport', SPORT_DEFAULT);

// 运动记录只保留最近 7 天，避免旧数据长期堆积
function pruneSportHistory() {
  const cutoff = toISODate(addDays(new Date(), -6));
  Object.keys(sportState.history).forEach(function (date) {
    if (date < cutoff) delete sportState.history[date];
  });
}

// 登录 / 切换账号后重新读取运动数据，避免继续使用脚本加载时的旧对象
// （旧对象会导致页面显示为空，并在下次保存时把服务器记录覆盖掉）
function reloadSportState() {
  const saved = loadData('sport', null);
  if (saved && saved.goal) {
    sportState = {
      goal: saved.goal,
      history: saved.history || {}
    };
  } else {
    sportState = {
      goal: { kcal: SPORT_DEFAULT.goal.kcal, steps: SPORT_DEFAULT.goal.steps,
              minutes: SPORT_DEFAULT.goal.minutes },
      history: {}
    };
  }
  pruneSportHistory();
}

reloadSportState();

// 小圆环半径 18，周长 = 2πr ≈ 113.1
const gaugeLength = 2 * Math.PI * 18;

// 今日实际数据：按日期存在 history 里，换天自动从 0 开始
function todaySport() {
  return sportState.history[toISODate(new Date())] || { kcal: 0, steps: 0, minutes: 0 };
}

// 本周合计：从本周一到今天
function weekSport() {
  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const startStr = toISODate(monday);
  const endStr = toISODate(today);
  const total = { kcal: 0, steps: 0, minutes: 0 };

  Object.keys(sportState.history).forEach(function (date) {
    if (date >= startStr && date <= endStr) {
      total.kcal += sportState.history[date].kcal || 0;
      total.steps += sportState.history[date].steps || 0;
      total.minutes += sportState.history[date].minutes || 0;
    }
  });
  return total;
}

// 完成率 = 热量 50% + 步数 30% + 时长 20%，三项分别封顶 100%
function sportPercent(actual, goal) {
  function ratio(value, target) {
    if (!target || target <= 0) return 0;
    return Math.min(1, (value || 0) / target);
  }
  return Math.round((ratio(actual.kcal, goal.kcal) * 0.5 +
    ratio(actual.steps, goal.steps) * 0.3 +
    ratio(actual.minutes, goal.minutes) * 0.2) * 100);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function renderExercise(key) {
  const isWeek = key === 'week';
  const data = isWeek ? weekSport() : todaySport();

  // 本周目标按已过天数折算，避免周初完成率永远很低
  const elapsed = isWeek ? ((new Date().getDay() + 6) % 7) + 1 : 1;
  const goal = {
    kcal: sportState.goal.kcal * elapsed,
    steps: sportState.goal.steps * elapsed,
    minutes: sportState.goal.minutes * elapsed
  };
  const percent = sportPercent(data, goal);

  document.getElementById('exKcal').textContent = formatNumber(data.kcal);
  document.getElementById('exSteps').textContent = formatNumber(data.steps);
  document.getElementById('exMinutes').textContent = formatNumber(data.minutes);
  document.getElementById('exPercent').textContent = percent + '%';

  const arc = document.getElementById('exGaugeArc');
  // 通过虚线偏移量控制圆弧长度
  arc.setAttribute('stroke-dashoffset', (gaugeLength * (1 - percent / 100)).toFixed(1));
}

// 把已保存的目标回填到输入框
function fillSportInputs() {
  document.getElementById('goalKcal').value = sportState.goal.kcal;
  document.getElementById('goalSteps').value = sportState.goal.steps;
  document.getElementById('goalMinutes').value = sportState.goal.minutes;
}

// 保存今日实际数据到对应日期，并刷新统计与评分
function saveSportForDate(key, data) {
  sportState.history[key] = data;
  pruneSportHistory();
  saveData('sport', sportState);

  const activeTab = document.querySelector('#sportTabs button.active');
  renderExercise(activeTab ? activeTab.dataset.tab : 'today');
  renderWeekPanel();
  refreshDietViews();
}

// 计时结束等场景仍默认写今天
function saveTodaySport(data) {
  saveSportForDate(toISODate(new Date()), data);
}

// 点「点击填写」：卡片里的数字就地变成输入框，回车或点别处保存
const sportFieldMeta = {
  kcal: { max: 9999, name: '热量' },
  steps: { max: 100000, name: '步数' },
  minutes: { max: 1440, name: '时长' }
};
document.querySelectorAll('#todayStats .ex-stat[data-field]').forEach(function (card) {
  card.addEventListener('click', function () {
    if (card.querySelector('.ex-inline-input')) return;
    const field = card.dataset.field;
    const meta = sportFieldMeta[field];
    const valueEl = card.querySelector('.value');
    const numberEl = valueEl ? valueEl.querySelector('span') : null;
    if (!meta || !numberEl) return;

    const input = document.createElement('input');
    input.type = 'number';
    input.min = '0';
    input.step = '1';
    input.className = 'ex-inline-input';
    input.value = String(todaySport()[field] || 0);
    numberEl.hidden = true;
    numberEl.after(input);
    input.focus();
    input.select();

    let finished = false;
    function finish(save) {
      if (finished) return;
      finished = true;
      if (save) {
        const value = parseInt(input.value, 10);
        if (!isFinite(value) || value < 0) {
          showToast('请输入 0 或正整数');
        } else {
          const data = Object.assign({}, todaySport());
          data[field] = Math.min(value, meta.max);
          saveTodaySport(data);
          showToast('已更新' + meta.name + '：' + data[field]);
        }
      }
      input.remove();
      numberEl.hidden = false;
      const activeTab = document.querySelector('#sportTabs button.active');
      renderExercise(activeTab ? activeTab.dataset.tab : 'today');
    }

    input.addEventListener('blur', function () { finish(true); });
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        finish(true);
      } else if (event.key === 'Escape') {
        finish(false);
      }
    });
  });
});

document.getElementById('saveSportGoal').addEventListener('click', function () {
  const goal = {
    kcal: parseInt(document.getElementById('goalKcal').value, 10),
    steps: parseInt(document.getElementById('goalSteps').value, 10),
    minutes: parseInt(document.getElementById('goalMinutes').value, 10)
  };

  if (!goal.kcal || !goal.steps || !goal.minutes ||
      goal.kcal <= 0 || goal.steps <= 0 || goal.minutes <= 0) {
    showToast('目标值需要大于 0');
    return;
  }

  sportState.goal = goal;
  saveData('sport', sportState);
  renderExercise('today');
  updateScores();
  showToast('运动目标已保存');
});

// ---------- 点击数据卡片填写今日数据 ----------
const sportDataMask = document.getElementById('sportDataMask');

// 当前选择用于记录 / 补记运动的日期
function sportDateValue() {
  const input = document.getElementById('sdDate');
  const today = toISODate(new Date());
  if (!input || !input.value) return today;
  return input.value > today ? today : input.value;
}

function fillSportDateData(key) {
  const data = sportState.history[key] || { kcal: 0, steps: 0, minutes: 0 };
  document.getElementById('sdKcal').value = data.kcal || 0;
  document.getElementById('sdSteps').value = data.steps || 0;
  document.getElementById('sdMinutes').value = data.minutes || 0;
}

// 打开运动数据弹窗：可指定日期（默认今天），用于补记某一天
function openSportDataForDate(key) {
  const today = toISODate(new Date());
  const dayKey = key && key <= today ? key : today;
  const input = document.getElementById('sdDate');
  if (input) {
    input.max = today;
    input.value = dayKey;
  }
  fillSportDateData(dayKey);

  const parts = dayKey.split('-');
  const title = document.getElementById('sdTitle');
  if (title) {
    title.textContent = dayKey === today
      ? '填写今日运动数据'
      : '填写 ' + Number(parts[1]) + ' 月 ' + Number(parts[2]) + ' 日运动数据';
  }
  openMask(sportDataMask);
}

const sdDateInput = document.getElementById('sdDate');
if (sdDateInput) {
  sdDateInput.addEventListener('change', function () {
    const today = toISODate(new Date());
    if (!sdDateInput.value || sdDateInput.value > today) sdDateInput.value = today;
    fillSportDateData(sdDateInput.value);
  });
}

document.querySelectorAll('.ex-stat[data-field]').forEach(function (card) {
  card.addEventListener('click', function () {
    openSportDataForDate(toISODate(new Date()));
  });
});

document.getElementById('sdClose').addEventListener('click', function () {
  closeMask(sportDataMask);
});

document.getElementById('sdCancel').addEventListener('click', function () {
  closeMask(sportDataMask);
});

sportDataMask.addEventListener('click', function (event) {
  if (event.target === sportDataMask) closeMask(sportDataMask);
});

document.getElementById('sdSave').addEventListener('click', function () {
  const data = {
    kcal: parseInt(document.getElementById('sdKcal').value, 10) || 0,
    steps: parseInt(document.getElementById('sdSteps').value, 10) || 0,
    minutes: parseInt(document.getElementById('sdMinutes').value, 10) || 0
  };

  if (data.kcal < 0 || data.steps < 0 || data.minutes < 0) {
    showToast('数据不能为负数');
    return;
  }

  const key = sportDateValue();
  saveSportForDate(key, data);
  closeMask(sportDataMask);
  showToast((key === toISODate(new Date()) ? '今日' : dayLabelText(key)) + '运动数据已更新');
});

// ---------- 运动计时：开始后自动累计时长与热量 ----------
let sportStartTime = null;
let sportTimerId = null;

// 热量 = MET × 体重(kg) × 小时数（国际通用的 MET 估算公式）
function estimateSportKcal(name, minutes) {
  const sport = sportTypes.filter(function (item) {
    return item.name === name;
  })[0];
  const met = sport ? sport.met : 4;
  return Math.round(met * getCurrentWeight() * (minutes / 60));
}

function updateSportTimer() {
  if (!sportStartTime) return;
  const seconds = Math.floor((Date.now() - sportStartTime) / 1000);
  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0');
  const rest = String(seconds % 60).padStart(2, '0');
  document.getElementById('sportTimer').textContent = minutes + ':' + rest;
}

function startSportSession(name) {
  selectedSport = name;
  document.getElementById('activeSportName').textContent = name;
  document.getElementById('activeSport').hidden = false;
  sportStartTime = Date.now();
  updateSportTimer();
  clearInterval(sportTimerId);
  sportTimerId = setInterval(updateSportTimer, 1000);
  showToast('已开始运动：' + name + '，结束后自动统计时长与热量');
}

function stopSportSession() {
  if (!sportStartTime) return;

  const name = document.getElementById('activeSportName').textContent;
  const minutes = Math.max(1, Math.round((Date.now() - sportStartTime) / 60000));
  const kcal = estimateSportKcal(name, minutes);
  const today = todaySport();

  clearInterval(sportTimerId);
  sportTimerId = null;
  sportStartTime = null;
  document.getElementById('activeSport').hidden = true;
  document.getElementById('sportTimer').textContent = '00:00';

  saveTodaySport({
    kcal: today.kcal + kcal,
    steps: today.steps,
    minutes: today.minutes + minutes
  });

  showToast('已结束' + name + '：' + minutes + ' 分钟，约消耗 ' + kcal +
    ' kcal。可点击上方卡片按手环数据修正。');
}

// 点击运动分类直接开始；「球类」先让用户选择具体项目
document.querySelectorAll('.sport-pill').forEach(function (pill) {
  pill.addEventListener('click', function () {
    const name = pill.dataset.sport || pill.textContent.trim();

    if (name === '球类运动') {
      selectedSport = '';
      resetSportModal();
      renderSportBoards();
      renderSportBoard('球类运动');
      openMask(sportMask);
      return;
    }

    startSportSession(name);
  });
});

// ---------- 本周统计：点击某个日期，直接补记/修改那天的运动 ----------
let weekDaysCache = [];
let weekSelectedKey = '';

function weekDetailText(item) {
  const todayKey = toISODate(new Date());
  const head = '<b>' + (item.date.getMonth() + 1) + ' 月 ' + item.date.getDate() + ' 日</b><br>';

  if (item.key > todayKey) return head + '这天还没到，等当天再记录吧。';

  return head +
    '消耗：' + Math.round(item.data.kcal || 0) + ' kcal　步数：' + formatNumber(item.data.steps || 0) +
    '　时长：' + Math.round(item.data.minutes || 0) + ' 分钟' +
    '<br><span class="week-edit">点击日期可补记或修改这一天的运动</span>';
}

function selectWeekDay(key) {
  weekSelectedKey = key;
  const grid = document.getElementById('weekGrid');
  if (grid) {
    grid.querySelectorAll('.week-day').forEach(function (node) {
      node.classList.toggle('selected', node.dataset.date === key);
    });
  }

  const detail = document.getElementById('weekDetail');
  const item = weekDaysCache.filter(function (day) { return day.key === key; })[0];
  if (!detail) return;
  detail.innerHTML = item ? weekDetailText(item) : '点击上方任意日期，可查看并记录当天的运动。';
}

function renderWeekPanel() {
  const panel = document.getElementById('weekPanel');
  if (!panel) return;

  const today = new Date();
  const start = addDays(today, -6); // 与睡眠、体重、饮食图表一致：近 7 天，今天在最后
  const days = [];

  for (let index = 0; index < 7; index++) {
    const day = addDays(start, index);
    const key = toISODate(day);
    const data = sportState.history[key] || { kcal: 0, steps: 0, minutes: 0 };
    days.push({ date: day, key: key, data: data });
  }
  weekDaysCache = days;

  const maxKcal = Math.max.apply(null, days.map(function (item) {
    return item.data.kcal || 0;
  }).concat([1]));

  panel.innerHTML = '<div class="week-grid" id="weekGrid"></div><div class="week-detail" id="weekDetail">点击上方任意日期，可查看并记录当天（近 7 天）的运动。</div>';
  const grid = document.getElementById('weekGrid');

  days.forEach(function (item) {
    const tile = document.createElement('div');
    tile.className = 'week-day' + (item.data.kcal || item.data.steps ? '' : ' empty');
    tile.dataset.date = item.key;
    const icon = item.data.kcal >= maxKcal * 0.6 && item.data.kcal > 0 ? 'i-flame' : 'i-activity';

    const isToday = item.key === toISODate(today);
    tile.innerHTML = '<div class="date">' + (item.date.getMonth() + 1) + '/' + item.date.getDate() +
      (isToday ? '<em>今天</em>' : '') + '</div>' +
      '<svg class="icon"><use href="#' + icon + '"></use></svg>' +
      '<div class="kcal">' + (item.data.kcal ? Math.round(item.data.kcal) + ' kcal' : '无记录') + '</div>';

    tile.addEventListener('click', function () {
      selectWeekDay(item.key);
      if (item.key > toISODate(new Date())) {
        showToast('这天还没到，不能提前记录');
        return;
      }
      openSportDataForDate(item.key);
    });

    grid.appendChild(tile);
  });

  if (weekSelectedKey && days.some(function (item) { return item.key === weekSelectedKey; })) {
    selectWeekDay(weekSelectedKey);
  }
}

document.querySelectorAll('#sportTabs button').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('#sportTabs button').forEach(function (b) {
      b.classList.toggle('active', b === btn);
    });

    const isWeek = btn.dataset.tab === 'week';
    document.getElementById('todayStats').hidden = isWeek;
    document.getElementById('weekPanel').classList.toggle('active', isWeek);
    renderExercise(btn.dataset.tab);
  });
});

// ---------- 运动类型：先选大类板块，再选具体项目 ----------
const sportBoards = [
  { name: '户外运动', desc: '健走、快走、慢跑、骑行、徒步、登山、游泳、轮滑' },
  { name: '球类运动', desc: '乒乓球、羽毛球、篮球、足球、网球、排球、台球' },
  { name: '形体运动', desc: '瑜伽、普拉提、健身操、力量训练、太极、舞蹈' },
  { name: '碎片化运动', desc: '爬楼梯、跳绳、开合跳、深蹲、平板支撑、工间操' }
];

const sportTypes = [
  { name: '健走', board: '户外运动', cal: '约 280 kcal/小时', color: '#5d7a4f', icon: 'i-footprints', met: 4.3 },
  { name: '快走', board: '户外运动', cal: '约 260 kcal/小时', color: '#7a9b5c', icon: 'i-footprints', met: 4.0 },
  { name: '慢跑', board: '户外运动', cal: '约 455 kcal/小时', color: '#a05a32', icon: 'i-run', met: 7.0 },
  { name: '户外骑行', board: '户外运动', cal: '约 350 kcal/小时', color: '#0e7c74', icon: 'i-bike', met: 6.8 },
  { name: '徒步', board: '户外运动', cal: '约 320 kcal/小时', color: '#0e7c74', icon: 'i-mountain', met: 6.0 },
  { name: '跑步', board: '户外运动', cal: '约 450 kcal/小时', color: '#a05a32', icon: 'i-run', met: 8.3 },
  { name: '登山', board: '户外运动', cal: '约 420 kcal/小时', color: '#3d5336', icon: 'i-mountain', met: 7.5 },
  { name: '游泳', board: '户外运动', cal: '约 500 kcal/小时', color: '#0e7c74', icon: 'i-swim', met: 7.0 },
  { name: '轮滑 / 滑板', board: '户外运动', cal: '约 455 kcal/小时', color: '#5e6c58', icon: 'i-activity', met: 7.0 },
  { name: '飞盘', board: '户外运动', cal: '约 260 kcal/小时', color: '#5d7a4f', icon: 'i-activity', met: 4.0 },
  { name: '乒乓球', board: '球类运动', cal: '约 360 kcal/小时', color: '#455c3d', icon: 'i-ball', met: 4.0 },
  { name: '羽毛球', board: '球类运动', cal: '约 420 kcal/小时', color: '#8a5a26', icon: 'i-ball', met: 5.5 },
  { name: '篮球', board: '球类运动', cal: '约 470 kcal/小时', color: '#a05a32', icon: 'i-ball', met: 6.5 },
  { name: '足球', board: '球类运动', cal: '约 500 kcal/小时', color: '#5d7a4f', icon: 'i-ball', met: 7.0 },
  { name: '网球', board: '球类运动', cal: '约 440 kcal/小时', color: '#7a9b5c', icon: 'i-ball', met: 6.0 },
  { name: '排球', board: '球类运动', cal: '约 260 kcal/小时', color: '#0e7c74', icon: 'i-ball', met: 4.0 },
  { name: '匹克球', board: '球类运动', cal: '约 295 kcal/小时', color: '#9c7a4f', icon: 'i-ball', met: 4.5 },
  { name: '台球', board: '球类运动', cal: '约 165 kcal/小时', color: '#5e6c58', icon: 'i-ball', met: 2.5 },
  { name: '瑜伽', board: '形体运动', cal: '约 180 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '普拉提', board: '形体运动', cal: '约 200 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '健身操', board: '形体运动', cal: '约 300 kcal/小时', color: '#a05a32', icon: 'i-dumbbell', met: 5.0 },
  { name: '力量训练', board: '形体运动', cal: '约 330 kcal/小时', color: '#455c3d', icon: 'i-dumbbell', met: 5.0 },
  { name: '拉伸放松', board: '形体运动', cal: '约 120 kcal/小时', color: '#5e6c58', icon: 'i-activity', met: 2.3 },
  { name: '太极', board: '形体运动', cal: '约 195 kcal/小时', color: '#5d7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '八段锦', board: '形体运动', cal: '约 165 kcal/小时', color: '#7a9b5c', icon: 'i-yoga', met: 2.5 },
  { name: '舞蹈', board: '形体运动', cal: '约 325 kcal/小时', color: '#a05a32', icon: 'i-activity', met: 5.0 },
  { name: '爬楼梯', board: '碎片化运动', cal: '约 500 kcal/小时', color: '#3d5336', icon: 'i-mountain', met: 8.8 },
  { name: '快走 10 分钟', board: '碎片化运动', cal: '约 280 kcal/小时', color: '#5d7a4f', icon: 'i-footprints', met: 4.3 },
  { name: '跳绳', board: '碎片化运动', cal: '约 600 kcal/小时', color: '#8a5a26', icon: 'i-activity', met: 10.0 },
  { name: '开合跳', board: '碎片化运动', cal: '约 480 kcal/小时', color: '#a05a32', icon: 'i-activity', met: 8.0 },
  { name: '深蹲', board: '碎片化运动', cal: '约 325 kcal/小时', color: '#455c3d', icon: 'i-dumbbell', met: 5.0 },
  { name: '平板支撑', board: '碎片化运动', cal: '约 245 kcal/小时', color: '#9c7a4f', icon: 'i-activity', met: 3.8 },
  { name: '原地高抬腿', board: '碎片化运动', cal: '约 520 kcal/小时', color: '#a05a32', icon: 'i-run', met: 8.0 },
  { name: '靠墙静蹲', board: '碎片化运动', cal: '约 195 kcal/小时', color: '#7a9b5c', icon: 'i-dumbbell', met: 3.0 },
  { name: '工间操', board: '碎片化运动', cal: '约 210 kcal/小时', color: '#5e6c58', icon: 'i-activity', met: 3.5 }
];

const sportMask = document.getElementById('sportMask');
let selectedSport = '';

// 第一层：四个运动板块
function renderSportBoards() {
  const box = document.getElementById('sportBoards');
  box.innerHTML = '';

  sportBoards.forEach(function (board) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'sport-board';
    btn.innerHTML = '<b>' + board.name + '</b><span>' + board.desc + '</span>';
    btn.addEventListener('click', function () {
      renderSportBoard(board.name);
    });
    box.appendChild(btn);
  });
}

function resetSportModal() {
  document.getElementById('sportBoards').hidden = false;
  document.getElementById('sportBoardHead').hidden = true;

  const grid = document.getElementById('sportGrid');
  grid.hidden = true;
  grid.innerHTML = '';
}

// 第二层：某个板块下的具体项目
function renderSportBoard(board) {
  document.getElementById('sportBoards').hidden = true;
  document.getElementById('sportBoardHead').hidden = false;
  document.getElementById('sportBoardName').textContent = board;

  const grid = document.getElementById('sportGrid');
  grid.hidden = false;
  grid.innerHTML = '';

  sportTypes.filter(function (sport) {
    return sport.board === board;
  }).forEach(function (sport) {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'sport-option' + (selectedSport === sport.name ? ' selected' : '');

    const avatar = document.createElement('span');
    avatar.className = 'sport-avatar';
    avatar.style.background = sport.color;
    avatar.innerHTML = '<svg class="icon"><use href="#' + sport.icon + '"></use></svg>';

    const info = document.createElement('span');
    const name = document.createElement('span');
    name.className = 'sport-name';
    name.textContent = sport.name;
    const cal = document.createElement('span');
    cal.className = 'sport-cal';
    cal.textContent = sport.cal;
    info.appendChild(name);
    info.appendChild(cal);

    option.appendChild(avatar);
    option.appendChild(info);

    option.addEventListener('click', function () {
      selectedSport = sport.name;
      grid.querySelectorAll('.sport-option').forEach(function (item) {
        item.classList.remove('selected');
      });
      option.classList.add('selected');
    });

    grid.appendChild(option);
  });
}

document.getElementById('sportBack').addEventListener('click', function () {
  selectedSport = '';
  resetSportModal();
  renderSportBoards();
});

document.getElementById('startSport').addEventListener('click', function () {
  selectedSport = '';
  resetSportModal();
  renderSportBoards();
  openMask(sportMask);
});

document.getElementById('sportClose').addEventListener('click', function () {
  closeMask(sportMask);
});

document.getElementById('sportCancel').addEventListener('click', function () {
  closeMask(sportMask);
});

sportMask.addEventListener('click', function (event) {
  if (event.target === sportMask) closeMask(sportMask);
});

document.getElementById('sportConfirm').addEventListener('click', function () {
  if (!selectedSport) {
    showToast('请先选择一种运动类型');
    return;
  }

  closeMask(sportMask);
  startSportSession(selectedSport);
});

document.getElementById('stopSport').addEventListener('click', function () {
  stopSportSession();
});

// ---------- 科学变美：目标与计划 ----------
const beautyState = {
  type: '',
  startWeight: 0,
  currentWeight: 0,
  targetWeight: 0,
  weeks: 0,
  times: 0
};

const beautyDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

// 每周运动次数对应的训练日
const beautyDayIndexes = {
  2: [0, 3],
  3: [0, 2, 4],
  4: [0, 2, 4, 6],
  5: [0, 1, 3, 5, 6],
  6: [0, 1, 2, 4, 5, 6],
  7: [0, 1, 2, 3, 4, 5, 6]
};

const beautyActivityPools = {
  '健身减脂': ['健走 40 分钟 + 拉伸', '力量训练 30 分钟', '户外骑行 45 分钟', '跳绳 20 分钟', '瑜伽拉伸 30 分钟'],
  '增肌塑形': ['上肢力量训练 30 分钟', '下肢力量训练 30 分钟', '核心训练 25 分钟', '游泳 30 分钟', '蛋白质补充 + 拉伸'],
  '体态改善': ['肩颈拉伸 15 分钟', '核心稳定训练 25 分钟', '瑜伽 30 分钟', '靠墙站立 10 分钟', '散步 30 分钟'],
  '提升体能': ['间歇跑 20 分钟', '跳绳 15 分钟', '核心训练 25 分钟', '游泳 30 分钟', '爬楼梯 10 分钟'],
  '缓解压力': ['瑜伽 30 分钟', '户外散步 30 分钟', '拉伸放松 20 分钟', '呼吸训练 10 分钟', '慢跑 20 分钟'],
  '改善睡眠': ['睡前拉伸 15 分钟', '晚饭后散步 30 分钟', '瑜伽 20 分钟', '呼吸训练 10 分钟', '轻力量训练 20 分钟'],
  '经期舒缓': ['经期拉伸 15 分钟', '散步 20 分钟', '猫式伸展 10 分钟', '腹式呼吸 10 分钟', '热敷放松 15 分钟']
};

function updateBeautyProgress() {
  let percent = 0;

  if (beautyState.type === '健身减脂' && beautyState.startWeight > beautyState.targetWeight) {
    percent = (beautyState.startWeight - beautyState.currentWeight) /
      (beautyState.startWeight - beautyState.targetWeight) * 100;
  } else if (beautyState.type === '增肌塑形' && beautyState.targetWeight > beautyState.startWeight) {
    percent = (beautyState.currentWeight - beautyState.startWeight) /
      (beautyState.targetWeight - beautyState.startWeight) * 100;
  }

  percent = Math.max(0, Math.min(100, percent));
  document.getElementById('beautyProgress').style.width = percent.toFixed(0) + '%';

  const isWeightType = beautyState.type === '健身减脂' || beautyState.type === '增肌塑形';
  document.getElementById('beautyProgressText').textContent =
    isWeightType ? Math.round(percent) + '%' : '进行中';
}

// 本周一到周日对应的日期，用于按日期记住每天的计划完成状态
function currentWeekDates() {
  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const dates = [];
  for (let i = 0; i < 7; i++) dates.push(toISODate(addDays(monday, i)));
  return dates;
}

// 生成计划：点击按钮与登录后恢复共用同一套逻辑，silent 时跳过校验与提示
function generateBeautyPlan(type, target, weeks, times, silent) {
  // 当前体重统一取记录/档案，不再用固定 60kg 兜底
  const current = getCurrentWeight();

  if (!silent) {
    if (!current) {
      showToast('请先在个人信息里填写体重，再制定变美计划');
      return false;
    }
    if (!target || target < 20 || target > 200) {
      showToast('请输入 20-200 kg 的目标体重');
      return false;
    }
    if (!weeks || weeks < 2 || weeks > 52) {
      showToast('目标周期请设置在 2-52 周');
      return false;
    }
    if (!times || times < 2 || times > 7) {
      showToast('每周运动次数请设置在 2-7 次');
      return false;
    }
    if (type === '健身减脂' && target >= current) {
      showToast('减脂目标体重应低于当前体重');
      return false;
    }
    if (type === '增肌塑形' && target <= current) {
      showToast('增肌目标体重应高于当前体重');
      return false;
    }
  }

  // 目标与当前体重方向不符时，恢复计划只做展示，不重算热量缺口
  const validTarget = target >= 20 && target <= 200;
  if (!validTarget) return false;

  beautyState.type = type;
  // 起始体重用于计算进度：恢复计划时沿用当时保存的值
  const previousPlan = loadData('beautyPlan', null);
  const startWeight = silent && previousPlan && previousPlan.startWeight
    ? Number(previousPlan.startWeight)
    : current;
  beautyState.startWeight = startWeight;
  beautyState.currentWeight = current;
  beautyState.targetWeight = target;
  beautyState.weeks = weeks;
  beautyState.times = times;

  const weeklyChange = Math.abs(current - target) / weeks;
  const dailyCalories = Math.round(weeklyChange * 7700 / 7);
  const isWeightType = type === '健身减脂' || type === '增肌塑形';

  document.getElementById('beautyCurrent').textContent = current > 0 ? current.toFixed(1) : '—';
  document.getElementById('beautyTargetText').textContent = target.toFixed(1);
  document.getElementById('beautyWeekly').textContent = isWeightType ? weeklyChange.toFixed(1) : '—';
  document.getElementById('beautyDeficit').textContent = isWeightType
    ? (type === '健身减脂' ? '-' : '+') + dailyCalories
    : '—';

  let summary = '';
  if (type === '健身减脂') {
    summary = '按每周约 ' + weeklyChange.toFixed(1) + ' kg 的节奏，预计 ' + weeks +
      ' 周达到目标体重。建议每周运动 ' + times +
      ' 次，有氧与力量结合，每日保持约 ' + dailyCalories + ' kcal 的热量缺口，并保证蛋白质摄入。';
    if (weeklyChange > 1) {
      summary += ' 当前目标略激进，建议把周期适当拉长，避免过度节食。';
    }
  } else if (type === '增肌塑形') {
    summary = '按每周约 ' + weeklyChange.toFixed(1) + ' kg 的节奏，预计 ' + weeks +
      ' 周达到目标。建议每周运动 ' + times +
      ' 次，以力量训练为主，每日增加约 ' + dailyCalories + ' kcal 的热量与充足蛋白质。';
    if (weeklyChange > 1) {
      summary += ' 体重增长过快容易增加脂肪，建议适当放缓。';
    }
  } else if (type === '体态改善') {
    summary = '以体态改善为主，建议每周训练 ' + times +
      ' 次，重点加强核心、肩背与拉伸放松；体重目标仅作为参考，不必过度追求数字。';
  } else {
    const extra = {
      '提升体能': '训练量循序渐进，每周比上周多 10% 左右，注意热身后再提高强度。',
      '缓解压力': '以呼吸训练、瑜伽和户外散步为主，帮助降低焦虑水平。',
      '改善睡眠': '训练尽量安排在睡前 2 小时以前，配合固定作息效果更好。',
      '经期舒缓': '经期以舒缓动作为主，避免跳跃与高强度训练，注意腹部保暖。'
    }[type] || '注意热身与拉伸，循序渐进。';
    summary = '本次以「' + type + '」为目标，建议每周训练 ' + times + ' 次。' + extra;
  }
  document.getElementById('beautySummary').textContent = summary;

  // 生成一周计划
  const activeDays = beautyDayIndexes[times] || [0, 2, 4, 6];
  const pool = beautyActivityPools[type] || beautyActivityPools['健身减脂'];
  // 已勾选过的日期，重新生成计划时保留
  const savedPlan = loadData('beautyPlan', {}) || {};
  const doneMap = savedPlan.done || {};
  const weekDates = currentWeekDates();
  const weekEl = document.getElementById('beautyWeek');
  weekEl.innerHTML = '';

  beautyDays.forEach(function (day, index) {
    const slot = activeDays.indexOf(index);
    const dateKey = weekDates[index];
    const row = document.createElement('div');
    row.className = 'plan-day';
    if (doneMap[dateKey]) row.classList.add('done');
    // 跟随日历：标出今天是哪一格，跨周后自动换成新一周的日期
    if (dateKey === toISODate(new Date())) row.classList.add('today');

    // 每天计划前的勾选框：完成后划线标记，并按日期保存，重新进页面仍保留
    const check = document.createElement('button');
    check.type = 'button';
    check.className = 'plan-check';
    check.textContent = '✓';
    check.title = '标记今天是否完成';
    check.addEventListener('click', function () {
      if (doneMap[dateKey]) delete doneMap[dateKey];
      else doneMap[dateKey] = true;
      row.classList.toggle('done', !!doneMap[dateKey]);
      saveData('beautyPlan', Object.assign({}, loadData('beautyPlan', {}), { done: doneMap }));
      showToast(doneMap[dateKey] ? '已标记完成' : '已取消完成');
    });

    const dayEl = document.createElement('span');
    dayEl.className = 'plan-day-label';
    dayEl.innerHTML = '<b>' + day + '</b><em class="plan-date">' +
      dateKey.slice(5).replace('-', '/') + '</em>';

    const activityEl = document.createElement('span');
    activityEl.textContent = slot === -1 ? '休息 / 轻松散步' : pool[slot % pool.length];

    row.appendChild(check);
    row.appendChild(dayEl);
    row.appendChild(activityEl);
    weekEl.appendChild(row);
  });

  document.getElementById('beautyEmpty').hidden = true;
  document.getElementById('beautyResultBody').hidden = false;
  document.getElementById('beautyWeightNow').value = '';

  // 生成计划后同步推荐饮食种类与体重曲线
  renderBeautyDietTip(type);
  renderWeightChart();

  updateBeautyProgress();

  // 计划的目标设定写回账号，下次登录可恢复
  saveData('beautyPlan', {
    type: type,
    targetWeight: target,
    weeks: weeks,
    times: times,
    startWeight: startWeight,
    done: doneMap
  });
  if (!silent) showToast('已生成' + type + '计划');
  return true;
}

document.getElementById('generatePlan').addEventListener('click', function () {
  generateBeautyPlan(
    document.getElementById('beautyType').value,
    parseFloat(document.getElementById('beautyTarget').value),
    parseInt(document.getElementById('beautyWeeks').value, 10),
    parseInt(document.getElementById('beautyTimes').value, 10),
    false
  );
});

// 登录后恢复上次保存的变美计划
function restoreBeautyPlan() {
  const plan = loadData('beautyPlan', null);
  if (!plan || !plan.type || !plan.targetWeight) return;

  document.getElementById('beautyType').value = plan.type;
  document.getElementById('beautyTarget').value = plan.targetWeight;
  document.getElementById('beautyWeeks').value = plan.weeks || 12;
  document.getElementById('beautyTimes').value = String(plan.times || 4);

  generateBeautyPlan(plan.type, Number(plan.targetWeight),
    Number(plan.weeks) || 12, Number(plan.times) || 4, true);
}

// 记录当前体重并更新目标进度
document.getElementById('logBeautyWeight').addEventListener('click', function () {
  const value = parseFloat(document.getElementById('beautyWeightNow').value);

  if (!beautyState.startWeight) {
    showToast('请先生成运动计划');
    return;
  }
  if (!value || value < 20 || value > 200) {
    showToast('请输入正确的体重');
    return;
  }

  beautyState.currentWeight = value;
  document.getElementById('beautyCurrent').textContent = value.toFixed(1);
  // 同步健康数据、个人档案与体重曲线，保证各处显示一致
  applyWeightChange(value);
  updateBeautyProgress();
  showToast('已记录当前体重：' + value.toFixed(1) + ' kg');
});

/* ==========================================================
   六、健康档案：性别视图、周期设置、状态标签与家人记录
   ========================================================== */

// ---------- 日期工具 ----------
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function addDays(date, days) {
  const result = new Date(date.getTime());
  result.setDate(result.getDate() + days);
  return result;
}

function parseISODate(value) {
  if (!value) return null;
  const parts = value.split('-');
  if (parts.length !== 3) return null;
  const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return isNaN(date.getTime()) ? null : date;
}

function toISODate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return date.getFullYear() + '-' + month + '-' + day;
}

function formatMD(date) {
  return (date.getMonth() + 1) + '月' + date.getDate() + '日';
}

function formatYMD(date) {
  return date.getFullYear() + '年' + (date.getMonth() + 1) + '月' + date.getDate() + '日';
}

// ---------- 根据性别切换视图 ----------
let currentGender = '女';

function applyGenderView() {
  const isFemale = currentGender === '女';

  // 女性健康档案已并入「健康数据」页，仅女性用户显示
  document.getElementById('femaleHealthSection').hidden = !isFemale;
  document.getElementById('pGender').value = currentGender;
}

// ---------- 生理周期：长度与日期都可自由选择 ----------
let periodDays = 5;                          // 经期长度（天）
let cycleDays = 28;                          // 周期长度（天）
let lastPeriodStart = null; // 最近一次经期开始日，未记录时为 null
let lastPeriodEnd = null;   // 结束日，null 表示经期还没结束或未记录

const periodDaysSelect = document.getElementById('periodDays');
const cycleDaysMainSelect = document.getElementById('cycleDaysMain');
const cycleDaysInput = document.getElementById('cycleDaysInput');

// 生成下拉选项
function fillSelect(select, from, to, unit, selected) {
  select.innerHTML = '';
  for (let i = from; i <= to; i++) {
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = i + ' ' + unit;
    if (i === selected) option.selected = true;
    select.appendChild(option);
  }
}

// 若记录出的天数不在预设范围内，动态补充选项
function ensureOption(select, value, unit) {
  const exists = Array.from(select.options).some(function (option) {
    return option.value === String(value);
  });
  if (!exists) {
    const option = document.createElement('option');
    option.value = String(value);
    option.textContent = value + ' ' + unit;
    select.appendChild(option);
  }
}

function renderCycle() {
  ensureOption(periodDaysSelect, periodDays, '天');
  ensureOption(cycleDaysMainSelect, cycleDays, '天');
  ensureOption(cycleDaysInput, cycleDays, '天');

  periodDaysSelect.value = String(periodDays);
  cycleDaysMainSelect.value = String(cycleDays);
  cycleDaysInput.value = String(cycleDays);

  document.getElementById('lastPeriodRange').textContent = '—';
  if (!lastPeriodStart) {
    ['ovulationDate', 'nextPeriodDate', 'fertileWindow', 'daysToPeriod'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = '—';
    });
    const empty = document.getElementById('cycleForecast');
    if (empty) {
      empty.innerHTML = '<b>经期预测</b>　还没有记录最近一次经期，' +
        '点上方「记录经期」填写后会自动计算下次经期、排卵日与易孕期。';
    }
    refreshFemaleRecordLock();
    return;
  }

  // 未记录结束日期时：还在经期内显示「进行中」，已超出经期长度则显示已结束
  const rangeEnd = lastPeriodEnd
    ? formatMD(lastPeriodEnd)
    : (inPeriodToday() ? '进行中' : '已结束（未记录结束日期）');
  document.getElementById('lastPeriodRange').textContent =
    formatMD(lastPeriodStart) + ' - ' + rangeEnd;

  // 下次经期：从最近一次经期开始按周期长度往后推，直到不早于今天
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let nextStart = addDays(lastPeriodStart, cycleDays);
  let guard = 0;
  while (nextStart < today && guard < 240) {
    nextStart = addDays(nextStart, cycleDays);
    guard += 1;
  }

  // 排卵日按“下次月经前 14 天”估算，易孕期取排卵日前 5 天到后 1 天
  const ovulation = addDays(nextStart, -14);
  document.getElementById('ovulationDate').textContent = formatMD(ovulation);
  document.getElementById('nextPeriodDate').textContent = formatMD(nextStart);
  document.getElementById('fertileWindow').textContent =
    formatMD(addDays(ovulation, -5)) + ' - ' + formatMD(addDays(ovulation, 1));

  const daysLeft = Math.round((nextStart - today) / MS_PER_DAY);
  document.getElementById('daysToPeriod').textContent = daysLeft + ' 天';

  // 当前阶段：经期中 / 经前 / 经期后
  const periodEnd = lastPeriodEnd || addDays(lastPeriodStart, periodDays - 1);
  let stage = '';
  if (today >= lastPeriodStart && today <= periodEnd) {
    const dayNo = Math.round((today - lastPeriodStart) / MS_PER_DAY) + 1;
    stage = '现在处于经期第 ' + dayNo + ' 天' +
      (lastPeriodEnd ? '，注意保暖与休息。' : '（结束后记得补记结束日期），注意保暖与休息。');
  } else if (daysLeft <= 7) {
    stage = '距离下次经期还有 ' + daysLeft + ' 天，可能进入经前不适期，可适当减少高强度运动。';
  } else {
    stage = '目前处于经期后阶段，距下次经期约 ' + daysLeft + ' 天，是保持规律运动的好时机。';
  }

  const forecast = [];
  for (let index = 0; index < 3; index++) {
    forecast.push('<span class="fc-chip">' + formatYMD(addDays(nextStart, cycleDays * index)) + '</span>');
  }

  const box = document.getElementById('cycleForecast');
  if (box) {
    box.innerHTML = '<b>经期预测</b>　' + stage +
      '<div style="margin-top:6px">未来 3 次预计开始：' + forecast.join('') + '</div>' +
      '<div style="margin-top:4px;color:#8a9984">预测仅作参考，实际日期会受作息、压力等因素影响。</div>';
  }

  refreshFemaleRecordLock();
}

fillSelect(periodDaysSelect, 3, 10, '天', periodDays);
fillSelect(cycleDaysMainSelect, 21, 40, '天', cycleDays);
fillSelect(cycleDaysInput, 21, 40, '天', cycleDays);

// 周期设置写回账号
function saveFemaleProfile() {
  saveData('femaleProfile', {
    periodDays: periodDays,
    cycleDays: cycleDays,
    lastPeriodStart: lastPeriodStart ? toISODate(lastPeriodStart) : '',
    periodEnd: lastPeriodEnd ? toISODate(lastPeriodEnd) : ''
  });
}

// 从账号取回周期设置
function applyFemaleProfile(profile) {
  if (!profile) return;
  const days = parseInt(profile.periodDays, 10);
  const cycle = parseInt(profile.cycleDays, 10);
  const start = parseISODate(profile.lastPeriodStart);
  if (days >= 1 && days <= 15) periodDays = days;
  if (cycle >= 15 && cycle <= 60) cycleDays = cycle;
  if (start) {
    // 超过两个周期之前的旧记录不再用于预测，避免展示已过去的排卵日/经期
    const ageDays = Math.round((todayStart() - start) / MS_PER_DAY);
    if (ageDays >= 0 && ageDays <= cycleDays * 2) lastPeriodStart = start;
  }
  if (Object.prototype.hasOwnProperty.call(profile, 'periodEnd')) {
    // 空字符串表示「经期还没结束」，保持进行中
    lastPeriodEnd = parseISODate(profile.periodEnd) || null;
  } else if (start) {
    // 旧数据没有结束日期字段，按原经期长度推算
    lastPeriodEnd = addDays(start, periodDays - 1);
  }
  renderCycle();
}

periodDaysSelect.addEventListener('change', function () {
  periodDays = parseInt(periodDaysSelect.value, 10);
  renderCycle();
  saveFemaleProfile();
});

cycleDaysMainSelect.addEventListener('change', function () {
  cycleDays = parseInt(cycleDaysMainSelect.value, 10);
  renderCycle();
  saveFemaleProfile();
});

// ---------- 弹窗开关辅助 ----------
function openMask(mask) {
  mask.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeMask(mask) {
  mask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

// ---------- 生理期记录弹窗 ----------
const periodMask = document.getElementById('periodMask');
const periodStartInput = document.getElementById('periodStart');
const periodEndInput = document.getElementById('periodEnd');

// 弹窗内实时预览经期长度与排卵日
function updatePeriodPreview() {
  const start = parseISODate(periodStartInput.value);
  const end = parseISODate(periodEndInput.value);
  const cycle = parseInt(cycleDaysInput.value, 10) || cycleDays;
  const daysEl = document.getElementById('periodPreviewDays');
  const ovulationEl = document.getElementById('periodPreviewOvulation');

  if (!start) {
    daysEl.textContent = '—';
    ovulationEl.textContent = '—';
    return;
  }

  daysEl.textContent = (end && end >= start)
    ? (Math.round((end - start) / MS_PER_DAY) + 1) + ' 天'
    : '进行中';
  ovulationEl.textContent = formatMD(addDays(start, cycle - 14));
}

function todayStart() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

// 经期窗口：已记录结束日期时以结束日期为准，未记录时按经期长度推算
function femalePeriodEnd() {
  if (!lastPeriodStart) return null;
  return lastPeriodEnd || addDays(lastPeriodStart, periodDays - 1);
}

// 今天是否处于经期时间内，用于控制「今日状态」与「经期感受」能否记录
function inPeriodToday() {
  const end = femalePeriodEnd();
  if (!lastPeriodStart || !end) return false;
  const today = todayStart();
  return today >= lastPeriodStart && today <= end;
}

// 不在经期时间内：两块记录入口置灰并给出提示，直到设置新的经期开始日期
function refreshFemaleRecordLock() {
  const locked = !inPeriodToday();
  const statusCard = document.querySelector('#femaleHealthSection .status-card');
  const feelCard = document.getElementById('periodFeel');

  if (statusCard) statusCard.classList.toggle('is-locked', locked);
  if (feelCard) feelCard.classList.toggle('is-locked', locked);

  const addBtn = document.getElementById('femaleAddTag');
  if (addBtn) addBtn.disabled = locked;

  const statusTip = document.getElementById('statusTip');
  if (statusTip) {
    if (locked) {
      statusTip.textContent = '不在经期时间内，设置新的经期开始日期后可继续记录。';
    } else {
      updateStatusTip(todayFemaleTags());
    }
  }

  const feelDate = document.getElementById('feelDate');
  if (feelDate) feelDate.disabled = locked;

  if (document.getElementById('periodFeelOptions')) renderPeriodFeel();
}

document.getElementById('openPeriod').addEventListener('click', function () {
  periodStartInput.value = lastPeriodStart ? toISODate(lastPeriodStart) : '';
  periodEndInput.value = lastPeriodEnd ? toISODate(lastPeriodEnd) : '';
  cycleDaysInput.value = String(cycleDays);
  updatePeriodPreview();
  openMask(periodMask);
});

[periodStartInput, periodEndInput].forEach(function (input) {
  input.addEventListener('change', updatePeriodPreview);
});

cycleDaysInput.addEventListener('change', function () {
  const value = parseInt(cycleDaysInput.value, 10);
  if (value >= 21 && value <= 40) {
    cycleDays = value;
    renderCycle();
    saveFemaleProfile();
  }
  updatePeriodPreview();
});

document.getElementById('periodClose').addEventListener('click', function () {
  closeMask(periodMask);
});

document.getElementById('periodCancel').addEventListener('click', function () {
  closeMask(periodMask);
});

periodMask.addEventListener('click', function (event) {
  if (event.target === periodMask) closeMask(periodMask);
});

// 只记录开始日期：结束日期等经期过去后再补
document.getElementById('savePeriodStart').addEventListener('click', function () {
  const start = parseISODate(periodStartInput.value);
  if (!start) {
    showToast('请先选择开始日期');
    return;
  }
  if (start > todayStart()) {
    showToast('开始日期不能晚于今天');
    return;
  }

  lastPeriodStart = start;
  lastPeriodEnd = null;
  renderCycle();
  saveFemaleProfile();
  closeMask(periodMask);
  showToast('已记录开始日期，经期结束后再来记录结束日期');
});

// 记录结束日期：完成后自动算出经期长度
document.getElementById('savePeriodEnd').addEventListener('click', function () {
  const start = parseISODate(periodStartInput.value);
  const end = parseISODate(periodEndInput.value);
  const nextCycle = parseInt(cycleDaysInput.value, 10);

  if (!start) {
    showToast('请先选择开始日期');
    return;
  }
  if (!end) {
    showToast('请选择结束日期');
    return;
  }
  if (start > todayStart()) {
    showToast('开始日期不能晚于今天');
    return;
  }
  if (end > todayStart()) {
    showToast('结束日期不能晚于今天');
    return;
  }
  if (end < start) {
    showToast('结束日期不能早于开始日期');
    return;
  }

  const days = Math.round((end - start) / MS_PER_DAY) + 1;
  if (days < 1 || days > 15) {
    showToast('经期长度需在 1-15 天之间');
    return;
  }
  if (!nextCycle || nextCycle < 21 || nextCycle > 40) {
    showToast('请选择正确的周期长度');
    return;
  }

  lastPeriodStart = start;
  lastPeriodEnd = end;
  periodDays = days;
  cycleDays = nextCycle;

  renderCycle();
  saveFemaleProfile();
  closeMask(periodMask);
  showToast('已记录结束日期，本次经期 ' + days + ' 天');
});

// ---------- 状态标签：从预设选项中多选 ----------
const femaleTagValues = ['轻微腹痛', '情绪平稳', '腰酸', '疲惫', '头痛', '失眠', '食欲不振', '状态良好'];

// 今日状态对应的小建议：勾选后立即更新提示
const statusAdvice = {
  '轻微腹痛': '腹部注意保暖，可用热水袋热敷，避免生冷食物与剧烈运动。',
  '腰酸': '减少久坐久站，睡前热敷腰部，可做猫式伸展放松腰背。',
  '疲惫': '今天以恢复为主，保证 7-9 小时睡眠，运动改为散步或拉伸。',
  '头痛': '规律饮水与进食，减少屏幕时间；若持续加重请及时就医。',
  '失眠': '睡前 1 小时远离手机，避免咖啡因，可尝试 4-7-8 呼吸法。',
  '食欲不振': '少量多餐，选择温热易消化的食物，如粥、面条、蒸蛋。',
  '状态良好': '状态不错，可以按计划进行中等强度运动，运动后注意补充蛋白质。',
  '情绪平稳': '情绪平稳，适合安排 20-30 分钟有氧运动，继续保持规律作息。'
};

function updateStatusTip(values) {
  const tip = document.getElementById('statusTip');
  if (!tip) return;

  const messages = values.map(function (value) {
    return statusAdvice[value];
  }).filter(Boolean);

  tip.textContent = messages.length
    ? '科学建议：' + messages.slice(0, 2).join(' ')
    : '科学建议：记录今日状态后，这里会给出对应的护理建议。';
}

function closeTagMenus() {
  document.querySelectorAll('.tag-menu.open').forEach(function (menu) {
    menu.classList.remove('open');
  });
}

function createTagEditor(config) {
  const tagsEl = document.getElementById(config.tagsId);
  const addBtn = document.getElementById(config.addBtnId);
  const menu = document.getElementById(config.menuId);
  const optionsEl = document.getElementById(config.optionsId);
  const selected = new Set(config.initial);

  // 重新绘制已选标签
  function renderTags() {
    tagsEl.querySelectorAll('.tag:not(.add)').forEach(function (tag) {
      tag.remove();
    });

    selected.forEach(function (value) {
      const tag = document.createElement('span');
      tag.className = 'tag';
      tag.textContent = value;

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'x';
      remove.textContent = '×';
      remove.title = '移除标签';
      remove.setAttribute('aria-label', '移除标签');
      remove.addEventListener('click', function () {
        selected.delete(value);
        renderTags();
        renderOptions();
        if (config.onChange) config.onChange(Array.from(selected));
      });

      tag.appendChild(remove);
      tagsEl.insertBefore(tag, addBtn);
    });

    updateStatusTip(Array.from(selected));
  }

  // 绘制可选项，点击切换选中状态
  function renderOptions() {
    optionsEl.innerHTML = '';
    config.values.forEach(function (value) {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'tag-option' + (selected.has(value) ? ' selected' : '');
      option.textContent = value;
      option.addEventListener('click', function () {
        if (selected.has(value)) {
          selected.delete(value);
        } else {
          selected.add(value);
        }
        option.classList.toggle('selected');
        renderTags(); // 勾选后立即同步标签区
        if (config.onChange) config.onChange(Array.from(selected));
      });
      optionsEl.appendChild(option);
    });
  }

  addBtn.addEventListener('click', function (event) {
    event.stopPropagation();
    closeTagMenus();
    renderOptions();
    menu.classList.add('open');
  });

  menu.addEventListener('click', function (event) {
    event.stopPropagation();
  });

  menu.querySelector('[data-close-tag]').addEventListener('click', function () {
    menu.classList.remove('open');
    renderTags();
  });

  renderTags();
}

// 今日状态标签按日期保存，便于跨设备查看当天记录
// 同一天的「流量/颜色/痛经」也存放在这条记录里，更新标签时不能把它们覆盖掉
function saveFemaleStatus(tags) {
  if (!inPeriodToday()) return;
  const map = loadData('femaleStatus', {}) || {};
  const today = toISODate(new Date());
  const entry = map[today] || {};
  entry.tags = tags;
  entry.note = entry.note || '';
  const empty = !tags.length && !entry.flow && !entry.color && !entry.pain && !entry.note;
  if (empty) {
    delete map[today];
  } else {
    map[today] = entry;
  }
  saveData('femaleStatus', map);
}

function todayFemaleTags() {
  const map = loadData('femaleStatus', {}) || {};
  const entry = map[toISODate(new Date())];
  return (entry && entry.tags) || [];
}

createTagEditor({
  tagsId: 'femaleTags',
  addBtnId: 'femaleAddTag',
  menuId: 'femaleTagMenu',
  optionsId: 'femaleTagOptions',
  values: femaleTagValues,
  initial: todayFemaleTags(),
  onChange: saveFemaleStatus
});

// 点击标签面板以外的地方时收起面板
document.addEventListener('click', function (event) {
  if (!event.target.closest('.tag-menu') && !event.target.closest('.tag.add')) {
    closeTagMenus();
  }
});

// ---------- 经期感受：流量 / 颜色 / 痛经（按日期记录） ----------
const FEEL_GROUPS = [
  { key: 'flow', label: '流量', options: [
    { value: '非常少量', fill: 18 }, { value: '少量', fill: 36 },
    { value: '中量', fill: 55 }, { value: '大量', fill: 74 },
    { value: '非常大量', fill: 92 }
  ] },
  { key: 'color', label: '颜色', options: [
    { value: '浅红色', dot: '#f7b6c8' }, { value: '鲜红色', dot: '#ea4a63' },
    { value: '深红色', dot: '#b21830' }, { value: '褐色', dot: '#96543a' },
    { value: '黑色', dot: '#3b2b26' }
  ] },
  { key: 'pain', label: '痛经', options: [
    { value: '完全不痛', dot: '#fde7ee' }, { value: '轻微痛', dot: '#f9c3d5' },
    { value: '比较痛', dot: '#f08fae' }, { value: '非常痛', dot: '#e05c88' },
    { value: '痛到极致', dot: '#c72a63' }
  ] }
];

const feelDateInput = document.getElementById('feelDate');
const feelOptionsBox = document.getElementById('periodFeelOptions');

function feelMap() {
  return loadData('femaleStatus', {}) || {};
}

function renderPeriodFeel() {
  const dateInput = document.getElementById('feelDate');
  const optionsBox = document.getElementById('periodFeelOptions');
  const tip = document.getElementById('feelTip');
  if (!dateInput || !optionsBox) return;

  // 经期结束后不再允许记录经期感受，直到设置新的经期开始日期
  if (!inPeriodToday()) {
    optionsBox.innerHTML = '<div class="pf-locked">不在经期时间内，设置新的经期开始日期后可继续记录。</div>';
    if (tip) tip.textContent = '不在经期时间内，暂不可记录经期感受。';
    return;
  }

  const date = dateInput.value || toISODate(new Date());
  const entry = feelMap()[date] || {};

  optionsBox.innerHTML = FEEL_GROUPS.map(function (group) {
    const options = group.options.map(function (option) {
      const dot = group.key === 'flow'
        ? '<span class="pf-dot"><i style="height:' + option.fill + '%"></i></span>'
        : '<span class="pf-dot" style="background:' + option.dot + '"></span>';
      const active = entry[group.key] === option.value;
      return '<button type="button" class="pf-opt" data-key="' + group.key +
        '" data-value="' + option.value + '" aria-pressed="' + (active ? 'true' : 'false') + '">' +
        dot + '<span class="pf-label">' + option.value + '</span></button>';
    }).join('');
    return '<div class="pf-group"><h4>' + group.label + '</h4>' +
      '<div class="pf-options">' + options + '</div></div>';
  }).join('');

  const parts = [];
  if (entry.flow) parts.push('流量：' + entry.flow);
  if (entry.color) parts.push('颜色：' + entry.color);
  if (entry.pain) parts.push('痛经：' + entry.pain);
  if (tip) {
    tip.textContent = parts.length
      ? formatMD(parseISODate(date)) + ' 已记录 · ' + parts.join(' · ') + '（再点一次可取消）'
      : '选择后会按日期自动保存，可左右滑动查看全部选项。';
  }
}

function saveFeel(key, value) {
  if (!inPeriodToday()) {
    showToast('不在经期时间内，设置新的经期开始日期后可继续记录');
    return;
  }
  const date = feelDateInput.value || toISODate(new Date());
  const map = feelMap();
  const entry = map[date] || { tags: [], note: '' };
  if (entry[key] === value) {
    delete entry[key];
  } else {
    entry[key] = value;
  }
  const empty = !(entry.tags || []).length && !entry.flow && !entry.color && !entry.pain && !entry.note;
  if (empty) {
    delete map[date];
  } else {
    map[date] = entry;
  }
  saveData('femaleStatus', map);
  renderPeriodFeel();
}

if (feelDateInput && feelOptionsBox) {
  const feelToday = toISODate(new Date());
  feelDateInput.max = feelToday;
  feelDateInput.value = feelToday;
  feelDateInput.addEventListener('change', renderPeriodFeel);
  feelOptionsBox.addEventListener('click', function (event) {
    const btn = event.target.closest('.pf-opt');
    if (btn) saveFeel(btn.dataset.key, btn.dataset.value);
  });
  renderPeriodFeel();
}

// ---------- 睡眠记录 ----------
function sleepParts(hours) {
  const total = Number(hours) || 0;
  const h = Math.floor(total);
  return { h: h, m: Math.round((total - h) * 60) };
}

function renderSleepToday() {
  const log = loadData('sleepLog', []) || [];
  const today = toISODate(new Date());
  const entry = log.find(function (item) {
    return item.date === today;
  });
  const box = document.getElementById('sleepToday');

  if (!entry) {
    box.innerHTML = '还没有记录今天的睡眠。' +
      '<button type="button" class="hint-link" data-focus="sleepHour">现在记录</button>';
    document.getElementById('sleepHour').value = '';
    document.getElementById('sleepMinute').value = '';
    return;
  }
  const parts = sleepParts(entry.hours);
  box.textContent = '今日已记录：' + parts.h + ' 小时 ' + parts.m + ' 分钟 · ' + entry.quality;
  document.getElementById('sleepHour').value = parts.h;
  document.getElementById('sleepMinute').value = parts.m;
  document.getElementById('sleepQuality').value = entry.quality;
}

document.getElementById('sleepForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const hourValue = parseFloat(document.getElementById('sleepHour').value);
  const minuteValue = parseFloat(document.getElementById('sleepMinute').value);
  const quality = document.getElementById('sleepQuality').value;
  const h = isNaN(hourValue) ? 0 : hourValue;
  const m = isNaN(minuteValue) ? 0 : minuteValue;

  if (h < 0 || h > 23 || m < 0 || m > 59) {
    showToast('请输入正确的小时（0-23）和分钟（0-59）');
    return;
  }
  const hours = h + m / 60;
  if (hours <= 0 || hours > 24) {
    showToast('睡眠时长需大于 0 且不超过 24 小时');
    return;
  }

  const log = (loadData('sleepLog', []) || []).slice();
  const today = toISODate(new Date());
  const record = { date: today, hours: hours, quality: quality, note: '' };
  const index = log.findIndex(function (item) {
    return item.date === today;
  });
  if (index >= 0) {
    log[index] = Object.assign({}, log[index], record);
  } else {
    log.push(record);
  }

  saveData('sleepLog', log);
  renderSleepToday();
  renderSleepWeek();
  showToast('睡眠记录已保存');
});

renderSleepToday();

// 最近一周睡眠柱形图
function renderSleepWeek() {
  const box = document.getElementById('sleepWeek');
  if (!box) return;

  const log = loadData('sleepLog', []) || [];
  const byDate = {};
  log.forEach(function (item) {
    byDate[item.date] = Number(item.hours) || 0;
  });

  const today = new Date();
  const days = [];
  for (let offset = 6; offset >= 0; offset--) {
    const day = addDays(today, -offset);
    const key = toISODate(day);
    days.push({
      key: key,
      label: (day.getMonth() + 1) + '/' + day.getDate(),
      hours: byDate[key] || 0
    });
  }

  const maxHours = Math.max.apply(null, days.map(function (day) {
    return day.hours;
  }).concat([8, 1]));

  const bars = days.map(function (day) {
    const height = day.hours ? Math.max(4, Math.round(day.hours / maxHours * 64)) : 4;
    return '<div class="sleep-bar" title="' + day.key + '">' +
      '<em class="em">' + (day.hours ? day.hours.toFixed(1) + 'h' : '') + '</em>' +
      '<i style="height:' + height + 'px"></i><span>' + day.label + '</span></div>';
  }).join('');

  const hasAny = days.some(function (day) { return day.hours > 0; });
  box.innerHTML = '<div class="sleep-bars">' + bars + '</div>' +
    '<div class="sleep-today" style="margin-top:6px">' +
    (hasAny ? '近 7 天记录，柱高按睡眠小时数显示。' : '近 7 天还没有睡眠记录，记录后会显示在这里。') +
    '</div>';
}

renderSleepWeek();

// ---------- 家人健康：成员、健康记录与关怀提醒 ----------
const familyMask = document.getElementById('familyMask');
const memberMask = document.getElementById('memberMask');
const reminderMask = document.getElementById('reminderMask');
const familyPersonSelect = document.getElementById('familyPerson');
const familyTypeSelect = document.getElementById('familyType');
const reminderMemberSelect = document.getElementById('reminderMember');

// 家人列表：默认空，由用户自己「添加家人」创建，不再预置示例档案
let familyMembers = loadData('familyMembers', []);

const todayDate = new Date();

// 健康记录
let familyRecords = loadData('familyRecords', []);

// 关怀提醒：默认空，避免把示例提醒当成用户自己的待办
let reminders = loadData('reminders', []);

function getMember(memberId) {
  return familyMembers.filter(function (member) {
    return member.id === memberId;
  })[0];
}

function memberLabel(member) {
  if (!member) return '家人';
  return member.relation + (member.name ? ' · ' + member.name : '');
}

// 取某位家人最近的一条记录
function latestRecord(memberId) {
  const records = familyRecords.filter(function (record) {
    return record.memberId === memberId;
  });
  if (!records.length) return null;
  return records.slice().sort(function (a, b) {
    return b.date.localeCompare(a.date);
  })[0];
}

// 渲染家人卡片
function renderFamilyMembers() {
  const grid = document.getElementById('familyGrid');
  grid.innerHTML = '';

  // 空状态：还没有家人档案时给出说明与入口，避免整块空白
  if (!familyMembers.length) {
    const empty = document.createElement('div');
    empty.className = 'family-empty';
    empty.innerHTML = '<p>还没有家人档案</p>' +
      '<span>添加家人后，可以记录血压、用药与复诊提醒，统一在这里查看。</span>';
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'btn-soft btn-small';
    addBtn.textContent = '添加家人';
    addBtn.addEventListener('click', function () {
      document.getElementById('openMember').click();
    });
    empty.appendChild(addBtn);
    grid.appendChild(empty);
    return;
  }

  familyMembers.forEach(function (member) {
    const card = document.createElement('div');
    card.className = 'person-card';

    const head = document.createElement('div');
    head.className = 'person-head';

    const avatar = document.createElement('div');
    avatar.className = 'person-avatar';
    avatar.textContent = member.relation.charAt(0);

    const info = document.createElement('div');
    const name = document.createElement('span');
    name.className = 'person-name';
    name.textContent = memberLabel(member);
    info.appendChild(name);

    if (member.age) {
      const age = document.createElement('span');
      age.className = 'person-age';
      age.textContent = member.age + '岁';
      info.appendChild(age);
    }

    head.appendChild(avatar);
    head.appendChild(info);
    card.appendChild(head);

    // 卡片上的三行关键信息：基础病史 / 常用药物 / 紧急联系人
    function appendInfoLine(label, value) {
      const line = document.createElement('div');
      line.className = 'family-line';
      line.appendChild(document.createTextNode(label));
      const text = document.createElement('b');
      text.textContent = value || '暂无';
      line.appendChild(text);
      card.appendChild(line);
    }

    appendInfoLine('基础病史', member.conditions);
    appendInfoLine('常用药物', member.medications);
    appendInfoLine('紧急联系人', emergencyText(member));

    // 最近记录
    const record = latestRecord(member.id);
    const recordLine = document.createElement('div');
    recordLine.className = 'family-line clickable';
    recordLine.appendChild(document.createTextNode('最近记录'));
    const recordValue = document.createElement('b');
    recordValue.textContent = record
      ? formatYMD(parseISODate(record.date)) + ' · ' + record.type + ' ›'
      : '暂无记录 ›';
    recordLine.appendChild(recordValue);
    card.appendChild(recordLine);

    // 点击整张卡片查看完整健康数据
    card.title = '点击查看完整健康档案';
    card.addEventListener('click', function () {
      openMemberDetail(member);
    });

    grid.appendChild(card);
  });
}

// 紧急联系人展示文本
function emergencyText(member) {
  if (!member) return '';
  const name = member.emergencyName || '';
  const phone = member.emergencyPhone || '';
  if (!name && !phone) return '未填写';
  return name + (phone ? (name ? ' · ' : '') + phone : '');
}

// 渲染某位家人的全部记录（在详情弹窗中展示）
function renderFamilyRecords(memberId) {
  const records = familyRecords.filter(function (record) {
    return record.memberId === memberId;
  }).sort(function (a, b) {
    return b.date.localeCompare(a.date);
  });

  if (!records.length) return '<div class="member-record-empty">暂无健康记录，点击「添加记录」为该家人建档。</div>';

  return records.map(function (record) {
    return '<div class="member-record"><span class="date">' + formatYMD(parseISODate(record.date)) +
      '</span><span>' + escapeHtml(record.type) +
      (record.content ? ' · ' + escapeHtml(record.content) : '') + '</span></div>';
  }).join('');
}

// 点击家人卡片：打开完整健康档案
function openMemberDetail(member) {
  const body = document.getElementById('memberDetailBody');
  if (!body || !member) return;

  document.getElementById('memberRecordsTitle').textContent = memberLabel(member) + ' · 健康档案';

  const pending = reminders.filter(function (reminder) {
    return reminder.memberId === member.id && !reminder.done;
  }).sort(function (a, b) {
    return a.date.localeCompare(b.date);
  });

  const infoRows = [
    { label: '基础病史', value: member.conditions },
    { label: '常用药物', value: member.medications },
    { label: '紧急联系人', value: emergencyText(member) }
  ].map(function (row) {
    return '<div class="detail-item"><span>' + row.label + '</span><b>' +
      escapeHtml(row.value || '暂无') + '</b></div>';
  }).join('');

  const reminderRows = pending.length
    ? pending.map(function (reminder) {
      return '<div class="member-record"><span class="date">' +
        formatMD(parseISODate(reminder.date)) + '</span><span>' +
        escapeHtml(reminder.title) + '</span></div>';
    }).join('')
    : '<div class="member-record-empty">暂无待办提醒，可在「关怀提醒」中添加。</div>';

  body.innerHTML =
    '<div class="member-detail-head">' +
      '<div class="person-avatar">' + escapeHtml(member.relation.charAt(0)) + '</div>' +
      '<div class="member-detail-name"><b>' + escapeHtml(memberLabel(member)) + '</b><span>' +
        (member.age ? member.age + ' 岁' : '年龄未填写') + '</span></div>' +
    '</div>' +
    '<div class="detail-grid">' + infoRows + '</div>' +
    '<h4 class="detail-title">健康记录</h4>' + renderFamilyRecords(member.id) +
    '<h4 class="detail-title">待办提醒</h4>' + reminderRows;

  openMask(document.getElementById('memberRecordsMask'));
}

// 简单的 HTML 转义，避免用户输入的内容破坏结构
function escapeHtml(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const memberRecordsMask = document.getElementById('memberRecordsMask');

document.getElementById('memberRecordsClose').addEventListener('click', function () {
  closeMask(memberRecordsMask);
});

memberRecordsMask.addEventListener('click', function (event) {
  if (event.target === memberRecordsMask) closeMask(memberRecordsMask);
});

// ---------- 常用提醒：可自定义，保存在本地长期使用 ----------
const DEFAULT_QUICK_REMINDERS = [
  { label: '测量血压', text: '提醒家人测量血压' },
  { label: '按时吃药', text: '提醒家人按时吃药' },
  { label: '陪伴散步', text: '陪家人散步 30 分钟' },
  { label: '复诊体检', text: '预约复诊 / 体检' },
  { label: '多喝水', text: '提醒家人多喝水' },
  { label: '注意保暖', text: '提醒家人注意保暖' }
];

let quickReminders = loadData('quickReminders', DEFAULT_QUICK_REMINDERS);

function renderQuickReminders() {
  const box = document.getElementById('quickReminderBox');
  if (!box) return;
  box.innerHTML = '<span>常用提醒</span>';

  quickReminders.forEach(function (item) {
    const chip = document.createElement('button');
    chip.className = 'quick-chip';
    chip.type = 'button';
    chip.textContent = item.label;
    chip.title = item.text;
    chip.addEventListener('click', function () {
      openReminderDialog(item.text, [toISODate(addDays(new Date(), 1))]);
    });
    box.appendChild(chip);
  });

  // 手动添加常用提醒
  const addBtn = document.createElement('button');
  addBtn.className = 'quick-chip';
  addBtn.type = 'button';
  addBtn.style.borderStyle = 'dashed';
  addBtn.textContent = '＋ 自定义';
  addBtn.addEventListener('click', function () {
    const text = window.prompt('输入常用提醒内容，例如：提醒奶奶测血糖');
    const value = (text || '').trim();
    if (!value) return;
    if (quickReminders.some(function (item) { return item.text === value; })) {
      showToast('这条常用提醒已存在');
      return;
    }
    quickReminders.push({ label: value, text: value });
    saveData('quickReminders', quickReminders);
    renderQuickReminders();
    showToast('已添加到常用提醒');
  });
  box.appendChild(addBtn);
}

// ---------- 提醒日期：支持一次选择多个 ----------
let reminderPickedDates = [];

function renderReminderDates() {
  const box = document.getElementById('reminderDateList');
  if (!box) return;
  box.innerHTML = '';

  if (!reminderPickedDates.length) {
    box.innerHTML = '<span class="date-empty">还没有选择日期，可在上方快捷选择或手动添加</span>';
    return;
  }

  reminderPickedDates.slice().sort().forEach(function (iso) {
    const tag = document.createElement('span');
    tag.className = 'date-tag';
    tag.innerHTML = '<span>' + iso.slice(5) + ' 周' + '日一二三四五六'[parseISODate(iso).getDay()] + '</span>';

    const del = document.createElement('button');
    del.type = 'button';
    del.textContent = '×';
    del.title = '移除这个日期';
    del.addEventListener('click', function () {
      reminderPickedDates = reminderPickedDates.filter(function (date) { return date !== iso; });
      renderReminderDates();
    });

    tag.appendChild(del);
    box.appendChild(tag);
  });
}

function addReminderDate(iso) {
  if (!iso) return;
  if (reminderPickedDates.indexOf(iso) !== -1) {
    showToast('这个日期已经选过啦');
    return;
  }
  reminderPickedDates.push(iso);
  reminderPickedDates.sort();
  renderReminderDates();
}

function openReminderDialog(title, dates) {
  renderMemberOptions();
  document.getElementById('reminderTitle').value = title || '';
  document.getElementById('reminderDate').value = '';
  reminderPickedDates = (dates || []).slice();
  renderReminderDates();
  openMask(reminderMask);
}

// 快捷日期按钮
document.querySelectorAll('.date-chip').forEach(function (btn) {
  btn.addEventListener('click', function () {
    addReminderDate(toISODate(addDays(new Date(), Number(btn.dataset.day))));
  });
});

// 手动添加日期：点按钮或直接回车
document.getElementById('reminderDateAdd').addEventListener('click', function () {
  const input = document.getElementById('reminderDate');
  if (!input.value) {
    showToast('请选择要添加的日期');
    return;
  }
  addReminderDate(input.value);
  input.value = '';
});

document.getElementById('reminderDate').addEventListener('keydown', function (event) {
  if (event.key !== 'Enter' || event.isComposing) return;
  event.preventDefault();
  document.getElementById('reminderDateAdd').click();
});

// 渲染关怀提醒
function renderReminders() {
  const list = document.getElementById('reminderList');
  list.innerHTML = '';

  const pendingCount = reminders.filter(function (reminder) {
    return !reminder.done;
  }).length;
  document.getElementById('reminderCount').textContent =
    pendingCount ? pendingCount + ' 条待办' : '暂无待办';

  if (!reminders.length) {
    const empty = document.createElement('div');
    empty.className = 'reminder-empty';
    empty.textContent = '暂无关怀提醒，点击「添加提醒」设置一条吧。';
    list.appendChild(empty);
    return;
  }

  const todayStr = toISODate(new Date());

  reminders.slice().sort(function (a, b) {
    if (a.done !== b.done) return a.done ? 1 : -1;
    return a.date.localeCompare(b.date);
  }).forEach(function (reminder) {
    const member = getMember(reminder.memberId);
    const target = parseISODate(reminder.date);
    const diffDays = Math.round((target - parseISODate(todayStr)) / MS_PER_DAY);

    const item = document.createElement('div');
    item.className = 'reminder-item' + (reminder.done ? ' done' : '');

    // 完成按钮
    const check = document.createElement('button');
    check.type = 'button';
    check.className = 'reminder-check';
    check.textContent = reminder.done ? '✓' : '';
    check.title = reminder.done ? '标记为未完成' : '标记为已完成';
    check.addEventListener('click', function () {
      reminder.done = !reminder.done;
      saveData('reminders', reminders);
      renderReminders();
      renderFamilyMembers();
      showToast(reminder.done ? '已完成这条关怀提醒' : '已恢复为待办');
    });

    const main = document.createElement('div');
    main.className = 'reminder-main';

    const title = document.createElement('div');
    title.className = 'reminder-title';
    title.textContent = reminder.title;

    const meta = document.createElement('div');
    meta.className = 'reminder-meta';
    meta.textContent = formatYMD(target) + ' · ' + memberLabel(member);

    main.appendChild(title);
    main.appendChild(meta);

    // 日期状态标签
    const badge = document.createElement('span');
    badge.className = 'reminder-badge';
    if (reminder.done) {
      badge.textContent = '已完成';
      badge.classList.add('done');
    } else if (diffDays === 0) {
      badge.textContent = '今天';
      badge.classList.add('today');
    } else if (diffDays === 1) {
      badge.textContent = '明天';
    } else if (diffDays < 0) {
      badge.textContent = '已逾期';
      badge.classList.add('overdue');
    } else {
      badge.textContent = formatMD(target);
    }

    // 删除这条提醒
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'reminder-del';
    del.textContent = '删除';
    del.title = '删除这条关怀提醒';
    del.addEventListener('click', function () {
      const index = reminders.indexOf(reminder);
      if (index === -1) return;
      reminders.splice(index, 1);
      saveData('reminders', reminders);
      renderReminders();
      renderFamilyMembers();
      showToast('已删除这条关怀提醒');
    });

    item.appendChild(check);
    item.appendChild(main);
    item.appendChild(badge);
    item.appendChild(del);
    list.appendChild(item);
  });
}

// 同步「记录 / 提醒」弹窗中的家人下拉框
function renderMemberOptions() {
  [familyPersonSelect, reminderMemberSelect].forEach(function (select) {
    const previous = select.value;

    select.innerHTML = '';
    familyMembers.forEach(function (member) {
      const option = document.createElement('option');
      option.value = member.id;
      option.textContent = memberLabel(member);
      select.appendChild(option);
    });

    const exists = familyMembers.some(function (member) {
      return member.id === previous;
    });
    if (exists) select.value = previous;
  });

  renderFamilyTypes();
}

// 仅「爱人」可以记录生理期
function renderFamilyTypes() {
  const member = getMember(familyPersonSelect.value);
  const types = member && member.relation === '爱人'
    ? ['体检', '用药', '生理期', '其他']
    : ['体检', '用药', '其他'];

  const previous = familyTypeSelect.value;
  familyTypeSelect.innerHTML = '';

  types.forEach(function (type) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    familyTypeSelect.appendChild(option);
  });

  if (types.indexOf(previous) !== -1) {
    familyTypeSelect.value = previous;
  }
}

familyPersonSelect.addEventListener('change', renderFamilyTypes);

// ---------- 添加健康记录弹窗 ----------
document.getElementById('openFamilyRecord').addEventListener('click', function () {
  renderMemberOptions();
  document.getElementById('familyDate').value = toISODate(new Date());
  openMask(familyMask);
});

document.getElementById('familyClose').addEventListener('click', function () {
  closeMask(familyMask);
});

document.getElementById('familyCancel').addEventListener('click', function () {
  closeMask(familyMask);
});

familyMask.addEventListener('click', function (event) {
  if (event.target === familyMask) closeMask(familyMask);
});

document.getElementById('familySave').addEventListener('click', function () {
  const member = getMember(familyPersonSelect.value);
  const type = familyTypeSelect.value;
  const date = parseISODate(document.getElementById('familyDate').value);
  const content = document.getElementById('familyContent').value.trim();

  if (!member) {
    showToast('请先添加家人信息');
    return;
  }
  if (!date) {
    showToast('请选择记录日期');
    return;
  }

  familyRecords.push({
    memberId: member.id,
    type: type,
    date: toISODate(date),
    content: content
  });
  saveData('familyRecords', familyRecords);

  renderFamilyMembers();

  document.getElementById('familyContent').value = '';
  closeMask(familyMask);
  showToast('已为' + memberLabel(member) + '添加' + type + '记录');
});

// ---------- 添加家人信息弹窗 ----------
document.getElementById('openMember').addEventListener('click', function () {
  document.getElementById('memberRelation').value = '';
  document.getElementById('memberAge').value = '';
  document.getElementById('memberName').value = '';
  document.getElementById('memberConditions').value = '';
  document.getElementById('memberMedications').value = '';
  document.getElementById('memberEmergencyName').value = '';
  document.getElementById('memberEmergencyPhone').value = '';
  openMask(memberMask);
});

document.getElementById('memberClose').addEventListener('click', function () {
  closeMask(memberMask);
});

document.getElementById('memberCancel').addEventListener('click', function () {
  closeMask(memberMask);
});

memberMask.addEventListener('click', function (event) {
  if (event.target === memberMask) closeMask(memberMask);
});

document.getElementById('memberSave').addEventListener('click', function () {
  const relation = document.getElementById('memberRelation').value.trim();
  const age = parseInt(document.getElementById('memberAge').value, 10);
  const name = document.getElementById('memberName').value.trim();
  const conditions = document.getElementById('memberConditions').value.trim();
  const medications = document.getElementById('memberMedications').value.trim();
  const emergencyName = document.getElementById('memberEmergencyName').value.trim();
  const emergencyPhone = document.getElementById('memberEmergencyPhone').value.trim();

  if (!relation) {
    showToast('请填写家人的称呼或关系');
    return;
  }

  familyMembers.push({
    id: 'm' + Date.now(),
    relation: relation,
    name: name,
    age: age || '',
    conditions: conditions,
    medications: medications,
    emergencyName: emergencyName,
    emergencyPhone: emergencyPhone
  });
  saveData('familyMembers', familyMembers);

  renderFamilyMembers();
  renderMemberOptions();
  closeMask(memberMask);
  showToast('已添加家人：' + relation);
});

// ---------- 添加关怀提醒弹窗 ----------
document.getElementById('openReminder').addEventListener('click', function () {
  openReminderDialog('', [toISODate(new Date())]);
});

document.getElementById('reminderClose').addEventListener('click', function () {
  closeMask(reminderMask);
});

document.getElementById('reminderCancel').addEventListener('click', function () {
  closeMask(reminderMask);
});

reminderMask.addEventListener('click', function (event) {
  if (event.target === reminderMask) closeMask(reminderMask);
});

document.getElementById('reminderSave').addEventListener('click', function () {
  const member = getMember(reminderMemberSelect.value);
  const title = document.getElementById('reminderTitle').value.trim();

  if (!member) {
    showToast('请先添加家人信息');
    return;
  }
  if (!title) {
    showToast('请填写提醒内容');
    return;
  }
  if (!reminderPickedDates.length) {
    showToast('请至少选择一个提醒日期');
    return;
  }

  // 每个选中的日期各生成一条提醒
  reminderPickedDates.slice().sort().forEach(function (date, index) {
    reminders.push({
      id: 'r' + Date.now() + '-' + index,
      memberId: member.id,
      title: title,
      date: date,
      done: false
    });
  });
  saveData('reminders', reminders);

  renderReminders();
  renderFamilyMembers();
  closeMask(reminderMask);
  showToast('已添加 ' + reminderPickedDates.length + ' 条关怀提醒');
});

// 初始化页面状态
renderCycle();
applyGenderView();
renderMemberOptions();
renderFamilyMembers();
renderReminders();
renderQuickReminders();

/* ==========================================================
   六之三、核心体征记录（数据读写见「零、数据层」）
   ========================================================== */

// ---------- 核心数据：修改弹窗 + 近一个月记录 ----------
const vitalMask = document.getElementById('vitalMask');
let currentVital = 'weight';

const vitalConfig = {
  weight: { title: '修改体重', fields: [{ key: 'weight', label: '体重（kg）', step: '0.1' }] },
  fat: { title: '修改体脂率', fields: [{ key: 'fat', label: '体脂率（%）', step: '0.1' }] },
  bmi: { title: '修改 BMI', fields: [{ key: 'bmi', label: 'BMI（保存后自动换算体重）', step: '0.1' }] },
  bp: {
    title: '修改血压',
    fields: [
      { key: 'systolic', label: '收缩压 / 高压', step: '1' },
      { key: 'diastolic', label: '舒张压 / 低压', step: '1' }
    ]
  },
  glucose: { title: '修改血糖', fields: [{ key: 'glucose', label: '空腹血糖（mmol/L）', step: '0.1' }] }
};

function loadVitalsHistory() {
  return loadData('vitalsHistory', {});
}

// 记录一次数据，只保留最近 30 天
function pushVitalRecord(key, text) {
  const history = loadVitalsHistory();
  const now = new Date();
  const cutoff = toISODate(addDays(now, -30));

  if (!history[key]) history[key] = [];
  history[key].push({
    date: toISODate(now) + ' ' + now.toTimeString().slice(0, 5),
    text: text
  });
  history[key] = history[key].filter(function (item) {
    return item.date.slice(0, 10) >= cutoff;
  }).slice(-60);
  saveData('vitalsHistory', history);
}

function renderVitalHistory(key) {
  const box = document.getElementById('vitalHistory');
  const list = (loadVitalsHistory()[key] || []).slice().reverse();

  if (!list.length) {
    box.innerHTML = '<div class="vital-history-empty">近一个月还没有记录。</div>';
    return;
  }

  box.innerHTML = list.map(function (item) {
    return '<div class="vital-history-row"><span>' + item.date + '</span><b>' + item.text + '</b></div>';
  }).join('');
}

function openVitalModal(key) {
  currentVital = key;
  const config = vitalConfig[key];
  document.getElementById('vitalTitle').textContent = config.title;

  const fields = document.getElementById('vitalFields');
  fields.innerHTML = '';
  config.fields.forEach(function (field) {
    const wrap = document.createElement('div');
    wrap.className = 'field';
    wrap.innerHTML = '<label for="vf_' + field.key + '">' + field.label + '</label>' +
      '<input id="vf_' + field.key + '" type="number" step="' + field.step + '">';
    fields.appendChild(wrap);
  });

  // 回填当前数值
  if (key === 'weight') document.getElementById('vf_weight').value = document.getElementById('weightValue').textContent;
  if (key === 'fat') document.getElementById('vf_fat').value = document.getElementById('fatValue').textContent;
  if (key === 'bmi') document.getElementById('vf_bmi').value = document.getElementById('bmiValue').textContent;
  if (key === 'glucose') document.getElementById('vf_glucose').value = document.getElementById('glucoseValue').textContent;
  if (key === 'bp') {
    const parts = document.getElementById('bpValue').textContent.split('/');
    document.getElementById('vf_systolic').value = parts[0] || '';
    document.getElementById('vf_diastolic').value = parts[1] || '';
  }

  renderVitalHistory(key);
  openMask(vitalMask);
}

document.querySelectorAll('[data-vital]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    openVitalModal(btn.dataset.vital);
  });
});

document.getElementById('vitalClose').addEventListener('click', function () {
  closeMask(vitalMask);
});

document.getElementById('vitalCancel').addEventListener('click', function () {
  closeMask(vitalMask);
});

vitalMask.addEventListener('click', function (event) {
  if (event.target === vitalMask) closeMask(vitalMask);
});

function setBmiDisplay(bmi) {
  if (!bmi || !isFinite(bmi)) {
    document.getElementById('bmiValue').textContent = '—';
    document.getElementById('bmiBadge').hidden = true;
    return;
  }
  document.getElementById('bmiValue').textContent = bmi.toFixed(1);
  const badge = document.getElementById('bmiBadge');
  badge.hidden = false;

  // 中国成人 BMI 标准：＜18.5 偏瘦，18.5–23.9 正常，24.0–27.9 超重，≥28.0 肥胖
  if (bmi < 18.5) {
    badge.textContent = '偏瘦';
    badge.className = 'badge warn';
  } else if (bmi < 24) {
    badge.textContent = '正常';
    badge.className = 'badge';
  } else if (bmi < 28) {
    badge.textContent = '超重';
    badge.className = 'badge warn';
  } else {
    badge.textContent = '肥胖';
    badge.className = 'badge warn';
  }
}

function currentHeightMeters() {
  const heightCm = currentHeightCm();
  return heightCm > 0 ? heightCm / 100 : 0;
}

/* ==========================================================
   核心体征：正常值范围与异常提醒
   标准来源：WS/T 428-2013（成人 BMI）、中国高血压防治指南、
            中国 2 型糖尿病防治指南、常用体成分参考值
   ========================================================== */
function currentHeightCm() {
  const saved = parseFloat(readProfile().height);
  if (saved > 0) return saved;
  const input = parseFloat(document.getElementById('pHeight').value);
  return input > 0 ? input : 0;
}

function setRangeState(id, text, warn) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'rr-state' + (warn ? ' warn' : '');
}

function renderVitalRanges() {
  const heightCm = currentHeightCm();
  const heightM = heightCm / 100;
  const weight = parseFloat(document.getElementById('weightValue').textContent);
  const bmi = parseFloat(document.getElementById('bmiValue').textContent);
  const fat = parseFloat(document.getElementById('fatValue').textContent);
  const glucose = parseFloat(document.getElementById('glucoseValue').textContent);
  const bp = (document.getElementById('bpValue').textContent || '').split('/');
  const systolic = parseInt(bp[0], 10);
  const diastolic = parseInt(bp[1], 10);
  const isFemale = (currentGender || document.getElementById('pGender').value) === '女';

  const warnings = [];

  // 体重：按正常 BMI 区间反推
  const lowWeight = 18.5 * heightM * heightM;
  const highWeight = 23.9 * heightM * heightM;
  document.getElementById('refWeight').textContent = heightM
    ? lowWeight.toFixed(1) + '–' + highWeight.toFixed(1) + ' kg'
    : '填写身高后显示';

  const tip = document.getElementById('vitalsTip');
  if (tip) tip.hidden = heightM > 0;

  if (weight && heightM) {
    if (weight < lowWeight) {
      setRangeState('stateWeight', '偏低', true);
      warnings.push('体重 ' + weight.toFixed(1) + ' kg 低于参考下限 ' + lowWeight.toFixed(1) +
        ' kg（BMI＜18.5），建议增加优质蛋白与主食摄入。');
    } else if (weight > highWeight) {
      setRangeState('stateWeight', '偏高', true);
      warnings.push('体重 ' + weight.toFixed(1) + ' kg 高于参考上限 ' + highWeight.toFixed(1) +
        ' kg（BMI＞23.9），建议控制总热量并增加日常活动。');
    } else {
      setRangeState('stateWeight', '正常', false);
    }
  }

  if (bmi) {
    if (bmi < 18.5) {
      setRangeState('stateBmi', '偏瘦', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 属于偏瘦（＜18.5），建议保证三餐并适度增加力量训练。');
    } else if (bmi < 24) {
      setRangeState('stateBmi', '正常', false);
    } else if (bmi < 28) {
      setRangeState('stateBmi', '超重', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 属于超重（24.0–27.9），建议减少高油高糖食物并增加有氧运动。');
    } else {
      setRangeState('stateBmi', '肥胖', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 达到肥胖（≥28.0），建议在医生或营养师指导下制定减重计划。');
    }
  }

  // 体脂率：常用参考值，女性 20%–30%，男性 10%–20%
  const lowFat = isFemale ? 20 : 10;
  const highFat = isFemale ? 30 : 20;
  document.getElementById('refFat').textContent = isFemale ? '女 20%–30%' : '男 10%–20%';

  if (fat) {
    if (fat < lowFat) {
      setRangeState('stateFat', '偏低', true);
      warnings.push('体脂率 ' + fat.toFixed(1) + '% 低于' + (isFemale ? '女性' : '男性') +
        '参考下限 ' + lowFat + '%，建议适当增加健康脂肪与蛋白质摄入。');
    } else if (fat > highFat) {
      setRangeState('stateFat', '偏高', true);
      warnings.push('体脂率 ' + fat.toFixed(1) + '% 高于' + (isFemale ? '女性' : '男性') +
        '参考上限 ' + highFat + '%，建议结合力量训练与有氧运动。');
    } else {
      setRangeState('stateFat', '正常', false);
    }
  }

  // 血压：＜120/80 正常，120–139/80–89 正常高值，≥140/90 偏高
  if (systolic && diastolic) {
    if (systolic < 90 || diastolic < 60) {
      setRangeState('stateBp', '偏低', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 偏低，若伴随头晕乏力请及时就医。');
    } else if (systolic < 120 && diastolic < 80) {
      setRangeState('stateBp', '正常', false);
    } else if (systolic < 140 && diastolic < 90) {
      setRangeState('stateBp', '正常高值', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 处于正常高值（120–139/80–89），建议减少盐分摄入并规律监测。');
    } else {
      setRangeState('stateBp', '偏高', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 达到高血压范围（≥140/90），建议尽快就医评估。');
    }
  }

  // 空腹血糖：3.9–6.1 正常，6.1–7.0 空腹血糖受损，≥7.0 偏高
  if (glucose) {
    if (glucose < 3.9) {
      setRangeState('stateGlucose', '偏低', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 低于 3.9，注意按时进餐，必要时就医。');
    } else if (glucose <= 6.1) {
      setRangeState('stateGlucose', '正常', false);
    } else if (glucose < 7.0) {
      setRangeState('stateGlucose', '空腹血糖受损', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 处于空腹血糖受损区间（6.1–7.0），建议复查并咨询医生。');
    } else {
      setRangeState('stateGlucose', '偏高', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 达到糖尿病诊断参考值（≥7.0），请尽快就医确认。');
    }
  }

  // 异常提醒列表：先区分「未记录」「已记录且正常」「存在异常」三种情况
  const box = document.getElementById('abnormalBox');
  const list = document.getElementById('abnormalList');
  const recordedCount = [weight, bmi, fat, systolic, glucose].filter(function (value) {
    return isFinite(value) && value > 0;
  }).length;
  list.innerHTML = '';
  if (warnings.length) {
    box.classList.remove('ok');
    warnings.forEach(function (text) {
      const li = document.createElement('li');
      li.textContent = text;
      list.appendChild(li);
    });
  } else {
    box.classList.add('ok');
    const li = document.createElement('li');
    li.textContent = recordedCount
      ? '已记录的体征均在参考范围内。'
      : '尚未记录体征数据，点击各指标右侧「修改」即可录入并自动判断。';
    list.appendChild(li);
  }

  // BMI 公式代入当前身高体重
  if (weight) {
    const computed = weight / Math.pow(heightM, 2);
    document.getElementById('bmiFormulaValue').textContent =
      '当前：' + weight.toFixed(1) + ' ÷ ' + heightM.toFixed(2) + '² ≈ ' + computed.toFixed(1) +
      '（身高 ' + heightCm.toFixed(0) + ' cm）';
  }
}

// 体重变化后同步 BMI、个人档案与趋势
function applyWeightChange(weight) {
  document.getElementById('weightValue').textContent = weight.toFixed(1);
  document.getElementById('pWeight').value = weight.toFixed(1);

  // 同步到个人档案，刷新页面或重新登录后仍能恢复
  const profile = readProfile();
  profile.weight = weight;
  saveData('profile', profile);

  const heightM = currentHeightMeters();
  const bmi = heightM ? weight / (heightM * heightM) : 0;
  setBmiDisplay(bmi);
  renderVitalRanges();
  addWeightRecord(weight);
  return bmi;
}

document.getElementById('vitalSave').addEventListener('click', function () {
  const heightM = currentHeightMeters();

  if (currentVital === 'weight') {
    const value = parseFloat(document.getElementById('vf_weight').value);
    if (!value || value < 20 || value > 200) {
      showToast('请输入 20-200 kg 之间的体重');
      return;
    }
    const bmi = applyWeightChange(value);
    pushVitalRecord('weight', value.toFixed(1) + ' kg');
    if (bmi > 0) {
      pushVitalRecord('bmi', bmi.toFixed(1));
      showToast('体重已更新为 ' + value.toFixed(1) + ' kg');
    } else {
      showToast('体重已更新；填写身高后才能计算 BMI');
    }
  } else if (currentVital === 'fat') {
    const value = parseFloat(document.getElementById('vf_fat').value);
    if (!value || value < 3 || value > 60) {
      showToast('请输入 3-60% 之间的体脂率');
      return;
    }
    document.getElementById('fatValue').textContent = value.toFixed(1);
    pushVitalRecord('fat', value.toFixed(1) + ' %');
    showToast('体脂率已更新为 ' + value.toFixed(1) + '%');
  } else if (currentVital === 'bmi') {
    if (!heightM) {
      showToast('请先在「个人信息」里填写身高，再录入 BMI');
      return;
    }
    const bmi = parseFloat(document.getElementById('vf_bmi').value);
    if (!bmi || bmi < 12 || bmi > 45) {
      showToast('请输入 12-45 之间的 BMI');
      return;
    }
    const weight = bmi * heightM * heightM;
    applyWeightChange(weight);
    setBmiDisplay(bmi);
    pushVitalRecord('bmi', bmi.toFixed(1));
    pushVitalRecord('weight', weight.toFixed(1) + ' kg');
    showToast('已按 BMI 换算体重：' + weight.toFixed(1) + ' kg');
  } else if (currentVital === 'bp') {
    const systolic = parseInt(document.getElementById('vf_systolic').value, 10);
    const diastolic = parseInt(document.getElementById('vf_diastolic').value, 10);

    if (!systolic || !diastolic || systolic < 60 || systolic > 220 ||
        diastolic < 40 || diastolic > 140 || diastolic >= systolic) {
      showToast('请输入正确的血压，例如 118/76');
      return;
    }

    document.getElementById('bpValue').textContent = systolic + '/' + diastolic;
    saveData('bp', { systolic: systolic, diastolic: diastolic });
    pushVitalRecord('bp', systolic + '/' + diastolic + ' mmHg');
    showToast('血压已更新为 ' + systolic + '/' + diastolic + ' mmHg');
  } else if (currentVital === 'glucose') {
    const value = parseFloat(document.getElementById('vf_glucose').value);
    if (!value || value < 1 || value > 30) {
      showToast('请输入 1-30 mmol/L 之间的血糖');
      return;
    }
    document.getElementById('glucoseValue').textContent = value.toFixed(1);
    saveData('glucose', value);
    pushVitalRecord('glucose', value.toFixed(1) + ' mmol/L');
    showToast('血糖已更新为 ' + value.toFixed(1) + ' mmol/L');
  }

  closeMask(vitalMask);
  refreshDietViews();
  renderVitalRanges();
});

// 恢复上次保存的血压与血糖
const savedBp = loadData('bp', null);
if (savedBp && savedBp.systolic && savedBp.diastolic) {
  document.getElementById('bpValue').textContent = savedBp.systolic + '/' + savedBp.diastolic;
}
const savedGlucose = loadData('glucose', null);
if (savedGlucose) {
  document.getElementById('glucoseValue').textContent = Number(savedGlucose).toFixed(1);
}

// ---------- 体重历史与趋势曲线 ----------
// 体重记录：只保留最近 15 天
const WEIGHT_KEEP_DAYS = 15;
let weightHistory = loadData('weightHistory', []);

function pruneWeightHistory() {
  const cutoff = toISODate(addDays(new Date(), -(WEIGHT_KEEP_DAYS - 1)));
  weightHistory = weightHistory.filter(function (item) {
    return item.date >= cutoff;
  });
}

pruneWeightHistory();

function addWeightRecord(weight) {
  if (!weight || weight < 20 || weight > 200) return;

  const date = toISODate(new Date());
  const last = weightHistory[weightHistory.length - 1];

  // 同一天重复记录同一数值时跳过，否则每次都保留一个点，保证曲线上能看到变化
  if (last && last.date === date && Math.abs(last.weight - weight) < 0.01) {
    return;
  }
  weightHistory.push({ date: date, weight: weight });

  pruneWeightHistory();
  saveData('weightHistory', weightHistory);
  renderWeightChart();

  // 体重变化后重新计算营养目标与评分
  refreshDietViews();
}

// 曲线数据：图表只展示最近 7 天，同一天多次记录以最后一次为准
const WEIGHT_CHART_DAYS = 7;

function recentWeightData() {
  const cutoff = toISODate(addDays(new Date(), -(WEIGHT_CHART_DAYS - 1)));
  const byDate = {};

  weightHistory.forEach(function (item) {
    if (item.date < cutoff) return;
    byDate[item.date] = item.weight;
  });

  return Object.keys(byDate).sort().map(function (date) {
    return { date: date, weight: byDate[date] };
  });
}

function renderWeightChart() {
  // 体重曲线只保留在运动计划的目标进度中
  const boxes = ['weightChart'].map(function (id) {
    return document.getElementById(id);
  }).filter(Boolean);
  if (!boxes.length) return;

  let html = '';

  if (!weightHistory.length) {
    html = '<div class="weight-chart-empty">在「运动计划 · 记录当前体重」中记录后，这里会画出体重变化曲线。</div>';
  } else {
    const data = recentWeightData();
    const latest = data[data.length - 1].weight;
    const head = '<div class="weight-chart-head"><span>近 7 天体重趋势（' + data.length + ' 天有记录）</span><b>' +
      latest.toFixed(1) + ' kg</b></div>';

    if (data.length === 1) {
      html = head + '<div class="weight-chart-empty">再记录一次体重，就能看到趋势曲线。</div>';
    } else {
      const width = 440;
      const height = 176;
      const left = 32;
      const right = 14;
      const top = 16;
      const bottom = 50;
      const plotW = width - left - right;
      const plotH = height - top - bottom;

      const weights = data.map(function (item) { return item.weight; });
      const max = Math.max.apply(null, weights);
      const min = Math.min.apply(null, weights);
      const span = Math.max(1, max - min);

      function xFor(index) {
        return left + plotW * index / (data.length - 1);
      }

      function yFor(weight) {
        return top + plotH * (1 - (weight - min) / span);
      }

      let svg = '<svg viewBox="0 0 ' + width + ' ' + height + '">';

      // 最高 / 中间 / 最低三条参考线
      [max, (max + min) / 2, min].forEach(function (value, index) {
        const y = yFor(value).toFixed(1);
        svg += '<line x1="' + left + '" y1="' + y + '" x2="' + (width - right) + '" y2="' + y +
          '" stroke="#e9dfd2" stroke-width="1"' +
          (index === 1 ? ' stroke-dasharray="3 3"' : '') + '/>';
        svg += '<text x="4" y="' + (Number(y) + 3).toFixed(1) + '">' + value.toFixed(1) + '</text>';
      });

      const points = data.map(function (item, index) {
        return xFor(index).toFixed(1) + ',' + yFor(item.weight).toFixed(1);
      }).join(' ');

      svg += '<polyline points="' + points + '" fill="none" stroke="#455c3d" stroke-width="2" ' +
        'stroke-linejoin="round" stroke-linecap="round"/>';

      data.forEach(function (item, index) {
        svg += '<circle cx="' + xFor(index).toFixed(1) + '" cy="' + yFor(item.weight).toFixed(1) +
          '" r="3" fill="#fff" stroke="#455c3d" stroke-width="1.6"/>';
      });

      // 每个折点下方标注对应日期（旋转 45°，避免重叠）
      data.forEach(function (item, index) {
        const cx = xFor(index);
        const labelY = height - 30;
        svg += '<text x="' + cx.toFixed(1) + '" y="' + labelY +
          '" text-anchor="end" transform="rotate(-45 ' + cx.toFixed(1) + ' ' + labelY + ')" ' +
          'font-size="8" fill="#8a9984">' + item.date.slice(5) + '</text>';
      });
      svg += '</svg>';

      html = head + svg;
    }
  }

  boxes.forEach(function (box) {
    box.innerHTML = html;
  });
}

// ---------- 饮食：食物营养估算 ----------
// 说明：按常见食物给出每人份的估算值，用户可直接输入食物名称记录
const nutritionTable = [
  { keys: ['米饭', '白饭'], name: '米饭', portion: '1 碗 ≈ 150g', kcal: 230, protein: 4, carb: 50, fat: 1, fiber: 1 },
  { keys: ['面条', '拉面', '意面', '米粉', '馄饨', '饺子'], name: '面食', portion: '1 碗 ≈ 200g', kcal: 280, protein: 8, carb: 55, fat: 3, fiber: 2 },
  { keys: ['鸡蛋', '水煮蛋', '煎蛋', '蛋花'], name: '鸡蛋', portion: '1 个 ≈ 50g', kcal: 140, protein: 12, carb: 1, fat: 10, fiber: 0 },
  { keys: ['牛奶', '酸奶'], name: '奶制品', portion: '1 杯 ≈ 250ml', kcal: 130, protein: 8, carb: 12, fat: 5, fiber: 0 },
  { keys: ['鸡胸', '鸡肉', '瘦肉', '牛肉', '排骨'], name: '瘦肉', portion: '1 份 ≈ 100g', kcal: 165, protein: 25, carb: 0, fat: 6, fiber: 0 },
  { keys: ['鱼', '虾'], name: '鱼虾', portion: '1 份 ≈ 100g', kcal: 120, protein: 20, carb: 0, fat: 4, fiber: 0 },
  { keys: ['豆腐', '豆浆', '豆制品', '黄豆'], name: '豆制品', portion: '1 份 ≈ 100g', kcal: 110, protein: 10, carb: 6, fat: 5, fiber: 2 },
  { keys: ['蔬菜', '青菜', '西兰花', '菠菜', '沙拉', '生菜', '番茄', '黄瓜', '蘑菇'], name: '蔬菜', portion: '1 份 ≈ 150g', kcal: 80, protein: 4, carb: 10, fat: 2, fiber: 5 },
  { keys: ['水果', '苹果', '香蕉', '蓝莓', '橙', '葡萄', '西瓜'], name: '水果', portion: '1 份 ≈ 150g', kcal: 90, protein: 1, carb: 22, fat: 1, fiber: 3 },
  { keys: ['面包', '吐司'], name: '全麦面包', portion: '2 片 ≈ 60g', kcal: 180, protein: 7, carb: 30, fat: 3, fiber: 4 },
  { keys: ['燕麦', '粥'], name: '燕麦粥', portion: '1 碗 ≈ 250g', kcal: 160, protein: 6, carb: 27, fat: 3, fiber: 4 },
  { keys: ['坚果', '花生', '核桃'], name: '坚果', portion: '1 小把 ≈ 25g', kcal: 180, protein: 5, carb: 6, fat: 15, fiber: 2 },
  { keys: ['汉堡', '炸鸡', '薯条', '披萨'], name: '快餐', portion: '1 份（汉堡+薯条）', kcal: 550, protein: 20, carb: 50, fat: 28, fiber: 3 },
  { keys: ['奶茶', '可乐', '蛋糕', '甜品', '冰淇淋'], name: '含糖饮品 / 甜点', portion: '1 杯 / 1 块 ≈ 500ml / 100g', kcal: 300, protein: 3, carb: 45, fat: 10, fiber: 0 },
  { keys: ['咖啡'], name: '咖啡', portion: '1 杯 ≈ 250ml', kcal: 20, protein: 1, carb: 3, fat: 0, fiber: 0 }
];

const defaultNutrition = { kcal: 150, protein: 6, carb: 20, fat: 5, fiber: 2 };

// 根据输入文字匹配食物，未匹配到则按普通一餐估算
function estimateNutrition(text) {
  const result = { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 };
  let matched = 0;

  nutritionTable.forEach(function (food) {
    const hit = food.keys.some(function (key) {
      return text.indexOf(key) !== -1;
    });
    if (!hit) return;

    result.kcal += food.kcal;
    result.protein += food.protein;
    result.carb += food.carb;
    result.fat += food.fat;
    result.fiber += food.fiber;
    matched += 1;
  });

  if (!matched) {
    result.kcal = defaultNutrition.kcal;
    result.protein = defaultNutrition.protein;
    result.carb = defaultNutrition.carb;
    result.fat = defaultNutrition.fat;
    result.fiber = defaultNutrition.fiber;
  }
  return result;
}

// ---------- 饮食记录（保留最近 30 天，支持两周对比） ----------
let mealLog = loadData('mealLog', []);

// 当前选择用于记录 / 补记饮食的日期
function mealDateValue() {
  const input = document.getElementById('mealDate');
  const today = toISODate(new Date());
  if (!input || !input.value) return today;
  return input.value > today ? today : input.value;
}

function saveMealRecord(meal, text, nutrition) {
  mealLog.push({
    date: mealDateValue(),
    meal: meal,
    text: text,
    kcal: nutrition.kcal,
    protein: nutrition.protein,
    carb: nutrition.carb,
    fat: nutrition.fat,
    fiber: nutrition.fiber,
    image: pendingMealImage || ''
  });
  pendingMealImage = '';

  // 只保留最近 30 天，避免数据无限增长
  const cutoff = toISODate(addDays(new Date(), -30));
  mealLog = mealLog.filter(function (item) {
    return item.date >= cutoff;
  });
  saveData('mealLog', mealLog);

  renderMealLog();
  refreshDietViews();
}

function recordMealEntry(meal, rawText) {
  const text = (rawText || '').trim();
  if (!text) return;
  saveMealRecord(meal, text, estimateNutrition(text));
  showToast('已记录' + meal + '：' + text);
}

// ---------- 输入食物后弹出分量参考弹窗 ----------
const foodMask = document.getElementById('foodMask');
const foodCountInput = document.getElementById('foodCount');
let pendingMeal = null;

// 根据输入文字匹配食物库
function matchFoods(text) {
  return nutritionTable.filter(function (food) {
    return food.keys.some(function (key) {
      return text.indexOf(key) !== -1;
    });
  });
}

// 把「茄子，汤圆，虾」这类输入拆成单个食物
function splitFoodTokens(text) {
  return String(text || '').split(/[\s,，、;；\/+＋&]+/).filter(function (item) {
    return item.length > 0;
  });
}

// 每种食物都能在本地库里找到，才直接用本地数据；否则交给 AI 拆分估算
function allFoodsKnown(text) {
  const tokens = splitFoodTokens(text);
  if (!tokens.length) return false;
  return tokens.every(function (token) {
    return nutritionTable.some(function (food) {
      return food.keys.some(function (key) { return token.indexOf(key) !== -1; });
    });
  });
}

function sumFoodNutrition(foods) {
  return foods.reduce(function (total, food) {
    return {
      kcal: total.kcal + food.kcal,
      protein: total.protein + food.protein,
      carb: total.carb + food.carb,
      fat: total.fat + food.fat,
      fiber: total.fiber + food.fiber
    };
  }, { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 });
}

function foodCountValue() {
  return parseFloat(foodCountInput.value) || 0;
}

function updateFoodTotal() {
  const box = document.getElementById('foodTotal');
  if (!pendingMeal) return;

  if (pendingMeal.pending && !(pendingMeal.matches || []).length) {
    box.textContent = '正在估算热量，稍等片刻就会显示具体数值。';
    return;
  }

  const count = foodCountValue();
  if (count < 0.25 || count > 10) {
    box.textContent = '份数需在 0.25～10 之间，例如半碗填 0.5。';
    return;
  }

  const total = sumFoodNutrition(pendingMeal.matches);
  box.textContent = '按 ' + count + ' 份计算：约 ' + Math.round(total.kcal * count) + ' kcal，' +
    '蛋白质 ' + (total.protein * count).toFixed(1) + 'g，碳水 ' + (total.carb * count).toFixed(0) +
    'g，脂肪 ' + (total.fat * count).toFixed(1) + 'g。';
}

// 按当前 pendingMeal 重绘弹窗内容（AI 返回后原地更新，不重复弹窗）
function renderFoodModal() {
  if (!pendingMeal) return;

  const matches = pendingMeal.matches || [];
  const pending = !!pendingMeal.pending;
  const summary = document.getElementById('foodSummary');
  const portions = document.getElementById('foodPortions');

  if (!matches.length) {
    summary.textContent = pending
      ? 'AI 正在估算「' + pendingMeal.text + '」的热量，请稍候…'
      : '这一句没有识别出具体食物，可以换个说法再试。';
    portions.innerHTML = '<div class="food-portion-row"><span>' +
      (pending ? '估算中…' : '例如：米饭 鸡胸肉 西兰花') + '</span><b>' +
      (pending ? '…' : '—') + '</b></div>';
  } else {
    summary.textContent = (pendingMeal.source === 'ai' ? 'AI 估算到 ' : '本餐识别到 ') +
      matches.length + ' 种食物：' + matches.map(function (food) {
        return food.name;
      }).join('、') + (pending ? '（其他食物还在估算…）' : '');
    portions.innerHTML = matches.map(function (food) {
      return '<div class="food-portion-row"><span>' + food.name + ' · 参考分量 ' + food.portion +
        '</span><b>' + food.kcal + ' kcal / 份</b></div>';
    }).join('');
  }

  updateFoodTotal();
}

// 弹出分量参考弹窗（source: local 食物库 / ai 模型估算；pending 表示 AI 还在估算）
function showFoodModal(meal, text, matches, input, source, pending) {
  pendingMeal = {
    meal: meal,
    text: text,
    input: input,
    matches: matches || [],
    source: source,
    pending: !!pending
  };
  foodCountInput.value = 1;
  renderFoodModal();
  openMask(foodMask);
}

// 输入食物：先查本地食物库，查不到就让 AI 估算，不限制菜名
function requestMealRecord(meal, rawText, input) {
  const text = (rawText || '').trim();
  if (!text) {
    showToast('请先输入吃了什么，例如：米饭 鸡胸肉 西兰花');
    return;
  }

  const matches = matchFoods(text);
  if (matches.length && allFoodsKnown(text)) {
    showFoodModal(meal, text, matches, input, 'local');
    return;
  }

  // 静态演示版没有后端，按常见一餐粗略估算
  if (!serverMode || !currentUser) {
    const rough = estimateNutrition(text);
    showFoodModal(meal, text, [{
      name: text, portion: '按常见一人份估算', kcal: rough.kcal,
      protein: rough.protein, carb: rough.carb, fat: rough.fat, fiber: rough.fiber
    }], input, 'ai');
    return;
  }

  // 先把弹窗立刻打开（显示估算中），AI 返回后原地补全，
  // 避免第一次点了没反应、用户以为失败而反复点击
  showFoodModal(meal, text, matches, input, 'ai', true);

  api('/api/ai/food', { method: 'POST', body: { text: text } })
    .then(function (result) {
      if (!pendingMeal || pendingMeal.text !== text) return;

      if (!result.ok || !result.data.foods) {
        // AI 不可用时，至少把本地识别到的食物用上，避免这一餐完全记不上
        pendingMeal.pending = false;
        pendingMeal.matches = matches || [];
        if (matches.length) pendingMeal.source = 'local';
        renderFoodModal();
        if (!matches.length) {
          showToast((result.data && result.data.error) || '估算失败，换个说法再试');
        }
        return;
      }

      pendingMeal.matches = result.data.foods.map(function (food) {
        return {
          name: food.name,
          portion: food.portion || '1 份',
          kcal: Number(food.kcal) || 0,
          protein: Number(food.protein) || 0,
          carb: Number(food.carb) || 0,
          fat: Number(food.fat) || 0,
          fiber: Number(food.fiber) || 0
        };
      });
      pendingMeal.source = 'ai';
      pendingMeal.pending = false;
      renderFoodModal();
    })
    .catch(function () {
      if (!pendingMeal || pendingMeal.text !== text) return;
      pendingMeal.pending = false;
      pendingMeal.matches = matches || [];
      if (matches.length) pendingMeal.source = 'local';
      renderFoodModal();
      showToast('网络不稳定，估算没完成，可以再点一次记录');
    });
}

foodCountInput.addEventListener('input', updateFoodTotal);

document.getElementById('foodClose').addEventListener('click', function () {
  closeMask(foodMask);
});

document.getElementById('foodCancel').addEventListener('click', function () {
  closeMask(foodMask);
});

foodMask.addEventListener('click', function (event) {
  if (event.target === foodMask) closeMask(foodMask);
});

document.getElementById('foodSave').addEventListener('click', function () {
  if (!pendingMeal) return;

  if (pendingMeal.pending && !(pendingMeal.matches || []).length) {
    showToast('正在估算热量，请稍等一两秒');
    return;
  }

  const count = foodCountValue();
  if (count < 0.25 || count > 10) {
    showToast('份数需在 0.25～10 之间');
    return;
  }

  const base = sumFoodNutrition(pendingMeal.matches);
  const label = pendingMeal.text + (count !== 1 ? '（' + count + ' 份）' : '');

  saveMealRecord(pendingMeal.meal, label, {
    kcal: base.kcal * count,
    protein: base.protein * count,
    carb: base.carb * count,
    fat: base.fat * count,
    fiber: base.fiber * count
  });

  if (pendingMeal.input) pendingMeal.input.value = '';
  const meal = pendingMeal.meal;
  pendingMeal = null;
  closeMask(foodMask);
  showToast('已记录' + meal + '：' + label);
});

function renderMealLog() {
  const box = document.getElementById('mealLog');
  if (!box) return;
  box.innerHTML = '';

  const today = toISODate(new Date());
  const selected = mealDateValue();
  const isToday = selected === today;
  const title = document.getElementById('mealLogTitle');
  if (title) {
    title.textContent = isToday ? '今日饮食记录' : dayLabelText(selected) + ' 饮食记录（补记）';
  }
  const items = mealLog.filter(function (item) { return item.date === selected; });

  if (!items.length) {
    box.innerHTML = '<div class="meal-log-empty">' + (isToday ? '今天' : dayLabelText(selected)) +
      '还没有记录，在上面的早餐 / 午餐 / 晚餐输入框输入食物后按回车即可添加。</div>';
    return;
  }

  items.forEach(function (item) {
    const chip = document.createElement('span');
    chip.className = 'meal-log-item';

    // 上传过餐食图片的记录带一个小缩略图
    if (item.image) {
      const thumb = document.createElement('img');
      thumb.className = 'meal-thumb';
      thumb.src = item.image;
      thumb.alt = '餐食图片';
      chip.appendChild(thumb);
    }

    chip.appendChild(document.createTextNode(
      item.meal + ' · ' + item.text + '（约 ' + Math.round(item.kcal) + ' kcal）'));

    const del = document.createElement('button');
    del.type = 'button';
    del.textContent = '×';
    del.title = '删除这条记录';
    del.addEventListener('click', function () {
      const index = mealLog.indexOf(item);
      if (index === -1) return;
      mealLog.splice(index, 1);
      saveData('mealLog', mealLog);
      renderMealLog();
      refreshDietViews();
      showToast('已删除这条饮食记录');
    });

    chip.appendChild(del);
    box.appendChild(chip);
  });
}

// 饮食记录日期：默认今天，可切换到前几日补记
const mealDateInput = document.getElementById('mealDate');
if (mealDateInput) {
  const mealToday = toISODate(new Date());
  mealDateInput.max = mealToday;
  mealDateInput.min = toISODate(addDays(new Date(), -30));
  mealDateInput.value = mealToday;
  mealDateInput.addEventListener('change', function () {
    const today = toISODate(new Date());
    if (!mealDateInput.value || mealDateInput.value > today) mealDateInput.value = today;
    renderMealLog();
  });
}

// 当前体重：只认一个来源——最近一次体重记录，其次个人档案，最后页面上的实际数值
function getCurrentWeight() {
  if (weightHistory.length) {
    return weightHistory[weightHistory.length - 1].weight;
  }
  const saved = parseFloat(readProfile().weight);
  if (saved > 0) return saved;
  const shown = parseFloat(document.getElementById('weightValue').textContent);
  return shown > 0 ? shown : 0;
}

// 活动水平由用户在下拉框中选择，不再由系统擅自推测运动量
function getActivityFactor() {
  const select = document.getElementById('dietActivity');
  const factor = select ? (parseFloat(select.value) || 1.375) : 1.375;

  let proteinPerKg = 1.2;
  if (factor >= 1.7) proteinPerKg = 1.6;
  else if (factor >= 1.55) proteinPerKg = 1.5;
  else if (factor >= 1.375) proteinPerKg = 1.35;

  return { factor: factor, proteinPerKg: proteinPerKg };
}

// 按个人资料 + 体重变化 + 运动量计算每日营养目标（Mifflin-St Jeor，年龄按 22 岁估算）
function getNutritionTargets() {
  const weight = getCurrentWeight();
  const height = currentHeightCm();
  const gender = document.getElementById('pGender').value || '女';
  const activity = getActivityFactor();

  // 没有体重或身高时不算目标值，避免用编造的身高（如 165cm）算出错误热量
  if (!weight || !height) {
    return {
      kcal: 0, bmr: 0, activity: activity.factor,
      protein: 0, carb: 0, fat: 0, fiber: 25, ready: false
    };
  }

  const bmr = gender === '男'
    ? 10 * weight + 6.25 * height - 5 * 22 + 5
    : 10 * weight + 6.25 * height - 5 * 22 - 161;
  const kcal = Math.round(bmr * activity.factor / 10) * 10;

  return {
    kcal: kcal,
    bmr: Math.round(bmr),
    activity: activity.factor,
    protein: Math.round(weight * activity.proteinPerKg),
    carb: Math.round(kcal * 0.5 / 4),
    fat: Math.round(weight * 0.8),
    fiber: 25,
    ready: true
  };
}

/* ---------- 顶部三项评分：随饮食、运动、体重数据自动更新 ---------- */
// 单项达成度：落在目标的 80%-120% 记满分，偏离越多扣分越多
function ratioScore(value, target) {
  if (!target) return 0;
  const ratio = value / target;

  if (ratio >= 0.8 && ratio <= 1.2) return 100;
  if (ratio < 0.8) return Math.max(0, ratio / 0.8 * 100);
  return Math.max(0, 100 - (ratio - 1.2) * 150);
}

// 饮食评分：取近 7 天有记录日期的平均达成度，没有记录则为 0
function computeDietScore() {
  const targets = getNutritionTargets();
  const today = new Date();
  let sum = 0;
  let days = 0;

  for (let offset = 0; offset < 7; offset++) {
    const key = toISODate(addDays(today, -offset));
    const day = dateRangeSum(key, key);
    if (!day.days) continue;

    sum += (ratioScore(day.total.protein, targets.protein) +
      ratioScore(day.total.carb, targets.carb) +
      ratioScore(day.total.fiber, targets.fiber) +
      ratioScore(day.total.fat, targets.fat) +
      ratioScore(day.total.kcal, targets.kcal)) / 5;
    days += 1;
  }

  return days ? Math.round(sum / days) : 0;
}

// 运动评分：今日目标完成率
function computeSportScore() {
  return sportPercent(todaySport(), sportState.goal);
}

// BMI 评分：正常区间满分，偏瘦 / 超重按程度扣分；没有体重时不参与评分
function computeBmiScore() {
  const weight = getCurrentWeight();
  if (!weight) return 0;
  const height = currentHeightMeters();
  if (!height) return 0;
  const bmi = weight / (height * height);

  if (bmi >= 18.5 && bmi < 24) return 100;
  if (bmi >= 24 && bmi < 28) return 80;
  if (bmi >= 17 && bmi < 18.5) return 75;
  return 60;
}

function setScore(id, value, hasData) {
  const num = Math.max(0, Math.min(100, Math.round(value)));
  const textEl = document.getElementById(id);
  const barEl = document.getElementById(id + 'Bar');
  const denEl = textEl && textEl.parentNode
    ? textEl.parentNode.querySelector('.score-den') : null;
  // 没有记录时不显示 0 分，显示占位符，避免新用户一进来就被低分劝退
  if (textEl) {
    textEl.textContent = hasData ? num : '—';
    textEl.classList.toggle('is-empty', !hasData);
  }
  if (denEl) denEl.hidden = !hasData;
  if (barEl) barEl.style.width = (hasData ? num : 0) + '%';
}

function updateScores() {
  const diet = computeDietScore();
  const sport = computeSportScore();
  const bmi = computeBmiScore();
  const total = diet * 0.4 + sport * 0.4 + bmi * 0.2;

  // 综合分依赖饮食与运动记录；只有体征时不给总分，避免「体征都正常却只有 20 分」的矛盾
  const hasRecord = diet > 0 || sport > 0;

  setScore('scoreDiet', diet, diet > 0);
  setScore('scoreSport', sport, sport > 0);
  setScore('scoreTotal', total, hasRecord);
  applyScoreMood(total, hasRecord);
  updateRecordStreak();

  // 新用户还没有任何记录时，解释评分为什么偏低，而不是只给一个红色的 20/100
  const hint = document.getElementById('heroHint');
  if (hint) hint.hidden = hasRecord;

  // 核心体征右侧环形评分同步
  const ringScore = document.getElementById('ringScore');
  const ringArc = document.getElementById('ringArc');
  if (ringScore) ringScore.textContent = hasRecord ? Math.round(total) + '%' : '—';
  if (ringArc) {
    const circumference = 2 * Math.PI * 52;
    ringArc.setAttribute('stroke-dashoffset',
      (circumference * (1 - (hasRecord ? total : 0) / 100)).toFixed(1));
  }
}

// ---------- 评分的视觉人格：疲惫 / 平稳 / 活力 + 近 7 天点亮 ----------
function scoreMoodOf(value) {
  if (value >= 85) return { key: 'vital', text: '活力' };
  if (value >= 60) return { key: 'steady', text: '平稳' };
  return { key: 'tired', text: '疲惫' };
}

function applyScoreMood(total, hasRecord) {
  const card = document.querySelector('.score-total');
  const pill = document.getElementById('statePill');
  if (!card || !pill) return;

  if (!hasRecord) {
    card.removeAttribute('data-mood');
    pill.setAttribute('data-mood', 'none');
    pill.textContent = '待记录';
    return;
  }

  const mood = scoreMoodOf(total);
  card.setAttribute('data-mood', mood.key);
  pill.setAttribute('data-mood', mood.key);
  pill.textContent = mood.text;
}

// 连续记录：近 7 天里有饮食、运动或体重记录就点亮一颗，今天那颗带呼吸动画
function updateRecordStreak() {
  const box = document.getElementById('stateDots');
  if (!box) return;

  const today = new Date();
  let html = '';
  let lit = 0;

  for (let offset = 6; offset >= 0; offset -= 1) {
    const key = toISODate(addDays(today, -offset));
    const hasMeal = dateRangeSum(key, key).days > 0;
    const entry = sportState.history[key];
    const hasSport = !!(entry && (entry.kcal || entry.steps || entry.minutes));
    const hasWeight = weightHistory.some(function (item) { return item.date === key; });
    const on = hasMeal || hasSport || hasWeight;
    if (on) lit += 1;
    html += '<i class="' + (on ? 'on ' : '') + (offset === 0 ? 'today' : '') + '"></i>';
  }

  box.innerHTML = html;
  const text = document.getElementById('stateText');
  if (text) {
    text.textContent = lit
      ? '近 7 天记录 ' + lit + ' 天，状态会随记录持续变化'
      : '今天记录一次，点亮第一颗';
  }
}

// ---------- 点击顶部评分查看分析与建议 ----------
const scoreMask = document.getElementById('scoreMask');

function scoreLevelText(value) {
  if (value >= 85) return '优秀';
  if (value >= 70) return '良好';
  if (value >= 60) return '一般';
  return '待改善';
}

function listHtml(items) {
  return '<ul>' + items.map(function (item) {
    return '<li>' + item + '</li>';
  }).join('') + '</ul>';
}

function buildDietAnalysis() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today);
  const weekStart = toISODate(addDays(new Date(), -6));
  const week = dateRangeSum(weekStart, today);

  if (!eaten.days) {
    return '<p>今天还没有饮食记录，暂时无法评估具体营养摄入。</p>' +
      '<p>建议先记录早餐、午餐或晚餐，评分和本页分析会随记录自动更新。</p>';
  }

  const html = ['<p>今天摄入约 ' + Math.round(eaten.total.kcal) + ' kcal（目标 ' + targets.kcal +
    ' kcal），蛋白质 ' + Math.round(eaten.total.protein) + 'g（目标 ' + targets.protein +
    'g），膳食纤维 ' + Math.round(eaten.total.fiber) + 'g（目标 ' + targets.fiber + 'g）。</p>'];

  const items = [];
  if (eaten.total.protein < targets.protein * 0.8) {
    items.push('蛋白质不足，建议增加鸡蛋、鱼虾、鸡胸肉或豆制品。');
  }
  if (eaten.total.fiber < targets.fiber * 0.6) {
    items.push('膳食纤维偏少，建议补充两份深色蔬菜和一份水果。');
  }
  if (eaten.total.kcal > targets.kcal * 1.15) {
    items.push('热量已超出目标，晚餐宜清淡，减少油炸与含糖饮料。');
  }
  if (eaten.total.carb < targets.carb * 0.6) {
    items.push('碳水化合物偏低，可适量补充糙米、燕麦或红薯。');
  }
  if (!items.length) {
    items.push('主要营养指标基本达标，继续保持规律三餐与足量饮水。');
  }

  html.push('<h4>本日评估</h4>' + listHtml(items));
  if (week.days) {
    html.push('<h4>近 7 天</h4><p>共记录 ' + week.days + ' 天，平均每日约 ' +
      Math.round(week.total.kcal / week.days) + ' kcal，平均蛋白质 ' +
      Math.round(week.total.protein / week.days) + 'g。</p>');
  }

  return html.join('');
}

function buildSportAnalysis() {
  const actual = todaySport();
  const goal = sportState.goal;
  const percent = computeSportScore();
  const week = weekSport();

  const html = ['<p>今日完成度 ' + percent + '%：消耗 ' + Math.round(actual.kcal) +
    ' / ' + goal.kcal + ' kcal，步数 ' + formatNumber(actual.steps) + ' / ' +
    formatNumber(goal.steps) + '，运动时长 ' + Math.round(actual.minutes) +
    ' / ' + goal.minutes + ' 分钟。</p>'];

  const items = [];
  if (!actual.minutes) {
    items.push('今天还没有运动记录，可以先从 20 分钟快走或拉伸开始。');
  }
  if (percent < 60) {
    items.push('距离目标还有差距，建议增加一次 20-30 分钟中等强度运动。');
  }
  if (actual.steps < goal.steps * 0.6) {
    items.push('步数偏少，可以把通勤中的一段路改为步行。');
  }
  if (actual.minutes > goal.minutes * 1.5) {
    items.push('今天运动量较大，注意补水与拉伸，避免连续高强度训练。');
  }
  if (!items.length) {
    items.push('今日目标完成良好，保持每周 3-5 次中等强度运动即可。');
  }

  html.push('<h4>评估与建议</h4>' + listHtml(items));
  html.push('<h4>本周累计</h4><p>消耗 ' + Math.round(week.kcal) + ' kcal，步数 ' +
    formatNumber(week.steps) + '，运动 ' + Math.round(week.minutes) + ' 分钟。</p>');

  return html.join('');
}

function buildTotalAnalysis() {
  const diet = computeDietScore();
  const sport = computeSportScore();
  const bmi = computeBmiScore();
  const weight = getCurrentWeight();
  const height = currentHeightMeters();
  const bmiValue = height > 0 ? weight / (height * height) : 0;

  const html = ['<p>综合评分 = 饮食 40% + 运动 40% + BMI 20%。当前：饮食 ' + diet +
    ' 分、运动 ' + sport + ' 分、BMI ' + bmi + ' 分（' +
    (bmiValue > 0 ? bmiValue.toFixed(1) : '待填写身高') + '）。</p>'];

  const items = [];
  if (diet < 60) items.push('饮食评分偏低：优先补足蛋白质与蔬菜，减少含糖饮料。');
  if (sport < 60) items.push('运动评分偏低：先把每日步数提升到目标的一半，再逐步增加时长。');
  if (bmi < 100 && bmiValue >= 24) items.push('BMI 偏高：建议每周 150 分钟中等强度有氧，并控制精制碳水。');
  if (bmi < 100 && bmiValue < 18.5) items.push('BMI 偏低：适当增加优质蛋白与主食，配合力量训练。');
  if (!items.length) items.push('各项指标都在良好区间，保持当前作息和运动频率即可。');

  html.push('<h4>优先改善</h4>' + listHtml(items));
  return html.join('');
}

function openScoreModal(type) {
  const dietScore = computeDietScore();
  const sportScore = computeSportScore();
  const values = {
    total: Math.round(dietScore * 0.4 + sportScore * 0.4 + computeBmiScore() * 0.2),
    diet: dietScore,
    sport: sportScore
  };
  const titles = {
    total: '综合健康评分分析',
    diet: '饮食健康评分分析',
    sport: '运动完成评分分析'
  };
  const bodies = {
    total: buildTotalAnalysis,
    diet: buildDietAnalysis,
    sport: buildSportAnalysis
  };

  const value = values[type];
  const hasData = value > 0;
  document.getElementById('scoreModalTitle').textContent = titles[type];
  document.getElementById('scoreModalValue').textContent = hasData ? value : '—';
  document.getElementById('scoreModalLevel').textContent = hasData ? scoreLevelText(value) : '暂无数据';
  document.getElementById('scoreModalBody').innerHTML = bodies[type]();
  openMask(scoreMask);
}

document.querySelectorAll('.score[data-score]').forEach(function (item) {
  item.addEventListener('click', function () {
    openScoreModal(item.dataset.score);
  });
});

document.getElementById('scoreClose').addEventListener('click', function () {
  closeMask(scoreMask);
});

scoreMask.addEventListener('click', function (event) {
  if (event.target === scoreMask) closeMask(scoreMask);
});

// 统计某个日期区间的营养合计与记录天数
function dateRangeSum(startStr, endStr) {
  const total = { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 };
  const days = {};

  mealLog.forEach(function (item) {
    if (item.date < startStr || item.date > endStr) return;
    total.kcal += item.kcal;
    total.protein += item.protein;
    total.carb += item.carb;
    total.fat += item.fat;
    total.fiber += item.fiber;
    days[item.date] = true;
  });

  return { total: total, days: Object.keys(days).length };
}

function renderNutrition() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today).total;

  // 目标未生成时显示「—」，避免出现 0/0g 这类假数据
  function macroText(value, target, unit) {
    return Math.round(value) + '/' + (target > 0 ? target + unit : '—');
  }

  document.getElementById('macroProtein').textContent = macroText(eaten.protein, targets.protein, 'g');
  document.getElementById('macroCarb').textContent = macroText(eaten.carb, targets.carb, 'g');
  document.getElementById('macroFiber').textContent = macroText(eaten.fiber, targets.fiber, 'g');
  document.getElementById('macroFat').textContent = macroText(eaten.fat, targets.fat, 'g');
  document.getElementById('macroKcal').textContent = macroText(eaten.kcal, targets.kcal, ' kcal');

  const rows = [
    { label: '蛋白质', value: eaten.protein, target: targets.protein, unit: 'g' },
    { label: '碳水化合物', value: eaten.carb, target: targets.carb, unit: 'g' },
    { label: '膳食纤维', value: eaten.fiber, target: targets.fiber, unit: 'g' },
    { label: '脂肪', value: eaten.fat, target: targets.fat, unit: 'g' },
    { label: '总热量', value: eaten.kcal, target: targets.kcal, unit: 'kcal' }
  ];

  const box = document.getElementById('nutriList');
  box.innerHTML = '';

  rows.forEach(function (row) {
    const percent = row.target ? Math.min(100, row.value / row.target * 100) : 0;
    const item = document.createElement('div');
    item.innerHTML =
      '<div class="nutri-head"><span>' + row.label + '</span><span><b>' +
      Math.round(row.value) + '</b> / ' + (row.target > 0 ? row.target : '—') + ' ' + row.unit + '</span></div>' +
      '<div class="nutri-bar' + (percent >= 100 ? ' over' : '') +
      '"><i style="width:' + percent.toFixed(1) + '%"></i></div>';
    box.appendChild(item);
  });

  // 把计算依据写清楚，避免“为什么体重一改热量就变”的困惑
  const note = document.getElementById('nutriNote');
  if (note) {
    note.textContent = targets.ready
      ? '计算依据：基础代谢 ' + targets.bmr + ' kcal × 活动系数 ' + targets.activity +
        ' ≈ ' + targets.kcal + ' kcal（Mifflin-St Jeor 公式）；蛋白质 ' + targets.protein +
        'g、脂肪 ' + targets.fat + 'g 按当前体重 ' + getCurrentWeight().toFixed(1) +
        'kg 计算。体重变化会改变基础代谢，所以目标值会随之调整。'
      : '还没有体重数据。先在「核心体征」或个人信息里记录身高体重，系统才会生成营养目标。';
  }
}

// 蛋白质达标天数（达到目标的 80%）
function countProteinDays(startStr, endStr, target) {
  const byDate = {};

  mealLog.forEach(function (item) {
    if (item.date < startStr || item.date > endStr) return;
    byDate[item.date] = (byDate[item.date] || 0) + item.protein;
  });

  return Object.keys(byDate).filter(function (date) {
    return byDate[date] >= target * 0.8;
  }).length;
}

// 蔬果记录次数
function countVegFruit(startStr, endStr) {
  const keys = ['蔬菜', '青菜', '西兰花', '菠菜', '沙拉', '生菜', '水果', '苹果', '香蕉', '蓝莓', '橙'];
  return mealLog.filter(function (item) {
    if (item.date < startStr || item.date > endStr) return false;
    return keys.some(function (key) { return item.text.indexOf(key) !== -1; });
  }).length;
}

// 本周 vs 上周对比
function renderWeekCompare() {
  const box = document.getElementById('weekCompare');
  if (!box) return;

  const today = new Date();
  const todayStr = toISODate(today);
  const thisStart = toISODate(addDays(today, -6));
  const lastEnd = toISODate(addDays(today, -7));
  const lastStart = toISODate(addDays(today, -13));

  const current = dateRangeSum(thisStart, todayStr);
  const previous = dateRangeSum(lastStart, lastEnd);
  const targets = getNutritionTargets();

  const curAvgKcal = current.days ? current.total.kcal / current.days : 0;
  const prevAvgKcal = previous.days ? previous.total.kcal / previous.days : 0;
  const curAvgProtein = current.days ? current.total.protein / current.days : 0;
  const prevAvgProtein = previous.days ? previous.total.protein / previous.days : 0;
  const curHit = countProteinDays(thisStart, todayStr, targets.protein);
  const prevHit = countProteinDays(lastStart, lastEnd, targets.protein);
  const curVeg = countVegFruit(thisStart, todayStr);
  const prevVeg = countVegFruit(lastStart, lastEnd);

  function diffCell(value, unit) {
    if (!value) return '<td>持平</td>';
    const cls = value > 0 ? 'up' : 'down';
    const sign = value > 0 ? '+' : '';
    return '<td class="' + cls + '">' + sign + Math.round(value) + ' ' + unit + '</td>';
  }

  let html = '<table><thead><tr><th>指标</th><th>本周</th><th>上周</th><th>变化</th></tr></thead><tbody>';
  html += '<tr><td>平均每日热量</td><td>' + Math.round(curAvgKcal) + ' kcal</td><td>' +
    Math.round(prevAvgKcal) + ' kcal</td>' + diffCell(curAvgKcal - prevAvgKcal, 'kcal') + '</tr>';
  html += '<tr><td>平均每日蛋白质</td><td>' + Math.round(curAvgProtein) + ' g</td><td>' +
    Math.round(prevAvgProtein) + ' g</td>' + diffCell(curAvgProtein - prevAvgProtein, 'g') + '</tr>';
  html += '<tr><td>蛋白质达标天数</td><td>' + curHit + ' 天</td><td>' + prevHit + ' 天</td>' +
    diffCell(curHit - prevHit, '天') + '</tr>';
  html += '<tr><td>蔬果记录次数</td><td>' + curVeg + ' 次</td><td>' + prevVeg + ' 次</td>' +
    diffCell(curVeg - prevVeg, '次') + '</tr>';
  html += '<tr><td>有记录天数</td><td>' + current.days + ' 天</td><td>' + previous.days + ' 天</td>' +
    diffCell(current.days - previous.days, '天') + '</tr>';
  html += '</tbody></table>';

  // 近 7 天热量柱状图
  const days = [];
  for (let offset = 6; offset >= 0; offset--) {
    const day = addDays(today, -offset);
    const key = toISODate(day);
    days.push({
      key: key,
      label: (day.getMonth() + 1) + '/' + day.getDate(),
      kcal: dateRangeSum(key, key).total.kcal
    });
  }

  const maxKcal = Math.max.apply(null, days.map(function (day) {
    return day.kcal;
  }).concat([targets.kcal, 1]));

  html += '<div class="mini-bars">';
  days.forEach(function (day) {
    const height = day.kcal ? Math.max(4, Math.round(day.kcal / maxKcal * 64)) : 4;
    html += '<button type="button" class="mini-bar' + (day.kcal ? '' : ' empty') +
      '" data-date="' + day.key + '">' +
      '<em>' + (day.kcal ? Math.round(day.kcal) : '') +
      '</em><i style="height:' + height + 'px"></i><span>' + day.label + '</span></button>';
  });
  html += '</div>';

  box.innerHTML = html;

  box.querySelectorAll('.mini-bar[data-date]').forEach(function (bar) {
    bar.addEventListener('click', function () {
      box.querySelectorAll('.mini-bar.active').forEach(function (node) {
        node.classList.remove('active');
      });
      bar.classList.add('active');
      openDayMeals(bar.dataset.date);
    });
  });
}

// ---------- 点击柱形图查看当天饮食 ----------
const dayMealMask = document.getElementById('dayMealMask');

function dayLabelText(key) {
  const date = parseISODate(key);
  if (!date) return key;
  return (date.getMonth() + 1) + ' 月 ' + date.getDate() + ' 日';
}

function openDayMeals(key) {
  const today = toISODate(new Date());
  document.getElementById('dayMealTitle').textContent =
    dayLabelText(key) + (key === today ? '（今天）' : '') + ' · 饮食记录';

  const items = mealLog.filter(function (item) { return item.date === key; });
  const body = document.getElementById('dayMealBody');
  const total = document.getElementById('dayMealTotal');

  if (!items.length) {
    body.innerHTML = '<div class="day-meal-empty">当天没有记录。<br>可在「记录日期」中选择这一天后补记饮食。</div>';
    total.textContent = '';
  } else {
    body.innerHTML = items.map(function (item) {
      return '<div class="day-meal-item"><span>' + item.meal + ' · ' + item.text + '</span><b>' +
        Math.round(item.kcal) + ' kcal</b></div>';
    }).join('');
    const sum = items.reduce(function (acc, item) {
      return acc + (Number(item.kcal) || 0);
    }, 0);
    const target = getNutritionTargets().kcal;
    total.textContent = '当天共 ' + items.length + ' 条记录，合计约 ' + Math.round(sum) +
      ' kcal（目标 ' + target + ' kcal）' +
      (sum > target * 1.15 ? '，略高于目标。' : sum < target * 0.6 ? '，摄入偏低。' : '，接近目标。');
  }
  openMask(dayMealMask);
}

document.getElementById('dayMealClose').addEventListener('click', function () {
  closeMask(dayMealMask);
});

document.getElementById('dayMealCancel').addEventListener('click', function () {
  closeMask(dayMealMask);
});

dayMealMask.addEventListener('click', function (event) {
  if (event.target === dayMealMask) closeMask(dayMealMask);
});

// ---------- 综合最近几天饮食的建议 ----------
function renderRecentDietAdvice() {
  const box = document.getElementById('recentDietAdvice');
  if (!box) return;

  const targets = getNutritionTargets();
  const today = new Date();
  const start = toISODate(addDays(today, -6));
  const end = toISODate(today);

  const days = {};
  let totalKcal = 0;
  let totalProtein = 0;
  let totalFiber = 0;
  let totalFat = 0;
  let vegFruit = 0;

  const vegKeys = ['蔬菜', '青菜', '西兰花', '菠菜', '沙拉', '生菜', '水果', '苹果', '香蕉', '蓝莓', '橙', '番茄'];

  mealLog.forEach(function (item) {
    if (item.date < start || item.date > end) return;
    days[item.date] = days[item.date] || { breakfast: false };
    totalKcal += Number(item.kcal) || 0;
    totalProtein += Number(item.protein) || 0;
    totalFiber += Number(item.fiber) || 0;
    totalFat += Number(item.fat) || 0;
    if (item.meal === '早餐') days[item.date].breakfast = true;
    if (vegKeys.some(function (key) {
      return String(item.text || '').indexOf(key) !== -1;
    })) {
      vegFruit += 1;
    }
  });

  const dayCount = Object.keys(days).length;
  if (!dayCount) {
    box.innerHTML = '<div class="ra-empty">近 7 天还没有饮食记录。连续记录 2-3 天后，这里会根据你的真实饮食给出综合建议。</div>';
    return;
  }

  const breakfastDays = Object.keys(days).filter(function (key) {
    return days[key].breakfast;
  }).length;
  const avgKcal = totalKcal / dayCount;
  const avgProtein = totalProtein / dayCount;
  const advice = [];

  if (dayCount < 3) {
    advice.push('目前只有 ' + dayCount + ' 天记录，建议连续记录 3 天以上，综合建议会更准确。');
  }
  if (avgKcal > targets.kcal * 1.12) {
    advice.push('近 ' + dayCount + ' 天平均每日约 ' + Math.round(avgKcal) + ' kcal，高于目标约 ' +
      Math.round(avgKcal - targets.kcal) + ' kcal，建议减少油炸、甜饮和夜宵。');
  } else if (avgKcal < targets.kcal * 0.7) {
    advice.push('近 ' + dayCount + ' 天平均每日仅 ' + Math.round(avgKcal) + ' kcal，摄入偏低，容易疲劳或反弹，建议三餐吃够。');
  } else {
    advice.push('近 ' + dayCount + ' 天平均每日约 ' + Math.round(avgKcal) + ' kcal，热量控制得比较稳。');
  }
  if (avgProtein < targets.protein * 0.8) {
    advice.push('平均蛋白质约 ' + Math.round(avgProtein) + 'g，低于目标 ' + targets.protein +
      'g，可在每餐加一个鸡蛋、一杯牛奶或一份豆制品。');
  } else {
    advice.push('平均蛋白质约 ' + Math.round(avgProtein) + 'g，已达到目标，注意分散到三餐吸收。');
  }
  if (vegFruit < dayCount) {
    advice.push('最近 ' + dayCount + ' 天蔬果记录偏少，建议每天至少两份深色蔬菜和一份水果。');
  }
  if (breakfastDays < Math.ceil(dayCount / 2)) {
    advice.push('有早餐记录的天数只有 ' + breakfastDays + ' 天，规律早餐有助于稳定上午的血糖和食欲。');
  }
  if (totalFat / dayCount > targets.fat * 1.2) {
    advice.push('平均脂肪摄入偏高，烹调尽量少油，少吃酥皮点心和肥肉。');
  }
  if (totalFiber / dayCount < targets.fiber * 0.6) {
    advice.push('膳食纤维不足，主食可换成一半杂粮，并增加蔬菜。');
  }

  box.innerHTML = '<div class="ra-head">根据最近 ' + dayCount + ' 天记录生成</div><ul>' +
    advice.map(function (item) { return '<li>' + item + '</li>'; }).join('') + '</ul>';
}

// 根据今日摄入自动生成建议
function buildDietAdvice() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today);

  if (!eaten.days) {
    return '今天还没有饮食记录。输入早餐、午餐或晚餐后按回车，系统会自动估算营养并给出建议。';
  }

  const tips = [];
  if (eaten.total.protein < targets.protein * 0.8) {
    tips.push('蛋白质还差约 ' + Math.round(targets.protein - eaten.total.protein) +
      'g，晚餐可以加一份鸡胸肉、鱼虾或豆腐。');
  }
  if (eaten.total.fiber < targets.fiber * 0.6) {
    tips.push('膳食纤维不足，建议再增加两份深色蔬菜和一份水果。');
  }
  if (eaten.total.kcal > targets.kcal * 1.15) {
    tips.push('今日热量已超出目标约 ' + Math.round(eaten.total.kcal - targets.kcal) +
      ' kcal，晚餐尽量清淡，少油少糖。');
  }
  if (eaten.total.carb < targets.carb * 0.6) {
    tips.push('碳水偏少可能影响精力，主食可以选择糙米、燕麦或红薯。');
  }

  // 结合运动与心情给出联动建议
  const sport = todaySport();
  if (sport.minutes > 0) {
    tips.push('今天已运动 ' + Math.round(sport.minutes) + ' 分钟，运动后 30 分钟内补充蛋白质和水分，更利于恢复。');
  }
  const mood = loadData('moodLog', {})[today];
  if (mood && (mood.mood === '疲惫' || mood.mood === '焦虑' || mood.mood === '低落')) {
    tips.push('今天心情偏' + mood.mood + '，晚餐尽量清淡，睡前拉伸 10 分钟并提前休息。');
  }

  if (!tips.length) {
    tips.push('今天的营养搭配比较均衡，注意多喝水、规律作息，继续保持。');
  }
  return tips.join('');
}

function refreshDietViews() {
  renderNutrition();
  renderWeekCompare();
  renderRecentDietAdvice();
  document.getElementById('dietTipText').textContent = buildDietAdvice();
  // 营养目标变化也会影响顶部评分
  updateScores();
}

// ---------- 科学变美：按计划类型推荐饮食种类 ----------
const beautyDietTips = {
  '健身减脂': [
    '优质蛋白：鸡胸肉、鱼虾、鸡蛋、无糖酸奶、豆腐，每餐一掌心',
    '复合碳水：糙米、燕麦、玉米、红薯，每餐一拳大小',
    '高纤维蔬菜：西兰花、菠菜、生菜、彩椒，每餐两拳',
    '低糖水果：苹果、蓝莓、猕猴桃，每日 200-350g',
    '少油少糖：以蒸煮为主，减少奶茶、油炸食品和夜宵'
  ],
  '增肌塑形': [
    '蛋白质加量：每日约 1.5-1.8g/kg 体重，分 4-5 餐摄入',
    '训练后 30 分钟内补充：乳清蛋白或牛奶 + 香蕉',
    '主食充足：燕麦、米饭、全麦面包，保证训练能量',
    '健康脂肪：坚果、牛油果、深海鱼',
    '补钙与维生素 D：牛奶、酸奶、蛋黄、深绿叶菜'
  ],
  '体态改善': [
    '足量蛋白：鸡蛋、豆制品、鱼肉，维持肌肉量',
    '钙 + 维生素 D：牛奶 300ml/天、豆制品、深绿叶菜',
    '抗氧化蔬果：番茄、彩椒、蓝莓、橙子',
    '少盐少钠：减少腌制食品，帮助减轻水肿',
    '规律三餐，避免长时间空腹或暴饮暴食'
  ],
  '提升体能': [
    '复合碳水：燕麦、糙米、全麦面包，训练前 1-2 小时补充',
    '优质蛋白：鸡胸肉、鱼虾、鸡蛋，训练后 30 分钟内补充',
    '补铁食物：瘦牛肉、猪肝、菠菜，搭配维 C 促进吸收',
    '充足饮水：运动前后各 200-300ml，出汗多时补充电解质',
    '少油少糖，避免训练前吃太饱'
  ],
  '缓解压力': [
    '富含镁的食物：香蕉、坚果、深绿叶菜，有助放松神经',
    '优质蛋白与复合碳水搭配，稳定血糖和情绪',
    '减少咖啡因与酒精，尤其下午之后',
    '规律进食，避免情绪性暴食',
    '多喝水，少量多次'
  ],
  '改善睡眠': [
    '晚餐清淡，睡前 2-3 小时不再进食',
    '助眠食物：牛奶、香蕉、燕麦、小米粥',
    '避免睡前咖啡、浓茶、酒精',
    '白天保证足够日照与活动量',
    '睡前可喝一小杯温牛奶'
  ],
  '经期舒缓': [
    '补铁：瘦红肉、动物肝脏、菠菜，搭配橙子等维 C 食物',
    '温热食物为主，减少生冷、冰饮',
    '适量补充钙与镁：牛奶、豆制品、坚果',
    '少盐，减轻水肿与腹胀',
    '少量多餐，避免空腹时间过长'
  ]
};

function renderBeautyDietTip(type) {
  const box = document.getElementById('beautyDietTip');
  if (!box) return;

  const tips = beautyDietTips[type] || beautyDietTips['健身减脂'];
  box.innerHTML = '<b>推荐饮食种类 · ' + type + '</b><ul>' +
    tips.map(function (tip) { return '<li>' + tip + '</li>'; }).join('') + '</ul>';
  box.hidden = false;
}

// ---------- 每日心情与小贴士 ----------
const moodTips = {
  '开心': '好心情值得被记住：把让你开心的事写下来，低落时回看会很有力量。也别忘了保持规律作息和运动，让好状态延续。',
  '平静': '平稳的一天适合做长期有益的事：散步 20 分钟、拉伸肩颈，或者比平时提前半小时入睡。',
  '疲惫': '身体在提醒你需要恢复。今晚尽量提前 30 分钟休息，睡前少看手机；明天把剧烈运动换成散步或拉伸。',
  '焦虑': '试试 4-7-8 呼吸法：吸气 4 秒、屏息 7 秒、呼气 8 秒，重复 4 轮。把担心的事写成清单，只处理今天能做的第一件。',
  '低落': '允许自己慢下来，先做一件很小的事（喝水、洗脸、出门走 5 分钟）。如果低落持续两周以上，建议寻求专业心理支持。'
};

let currentMood = '';

document.querySelectorAll('#moodPicker .mood-opt').forEach(function (btn) {
  btn.addEventListener('click', function () {
    currentMood = btn.dataset.mood;
    document.querySelectorAll('#moodPicker .mood-opt').forEach(function (item) {
      item.classList.toggle('selected', item === btn);
    });
    document.getElementById('moodTip').textContent = moodTips[currentMood];
  });
});

document.getElementById('saveMood').addEventListener('click', function () {
  if (!currentMood) {
    showToast('请先选择今天的心情');
    return;
  }

  const log = loadData('moodLog', {});
  const key = moodDateValue();
  log[key] = {
    mood: currentMood,
    note: document.getElementById('moodNote').value.trim()
  };
  saveData('moodLog', log);
  document.getElementById('moodTip').textContent = moodTips[currentMood];
  renderMoodWeek();
  renderWeekPanel();
  refreshDietViews();
  showToast((key === toISODate(new Date()) ? '今日' : dayLabelText(key)) + '心情已保存：' + currentMood);
});

// 心情与表情包对应关系
const moodEmojis = {
  '开心': '😄',
  '平静': '🙂',
  '疲惫': '😴',
  '焦虑': '😰',
  '低落': '😔'
};

function moodEmojiOf(mood) {
  return moodEmojis[mood] || '🙂';
}

// 当前选择用于记录 / 补记心情的日期
function moodDateValue() {
  const input = document.getElementById('moodDate');
  const today = toISODate(new Date());
  if (!input || !input.value) return today;
  return input.value > today ? today : input.value;
}

// 回显所选日期已保存的心情
function renderMoodForDate(date) {
  const key = date || toISODate(new Date());
  const isToday = key === toISODate(new Date());
  const saved = loadData('moodLog', {})[key];

  document.querySelectorAll('#moodPicker .mood-opt').forEach(function (btn) {
    btn.classList.toggle('selected', !!saved && btn.dataset.mood === saved.mood);
  });

  currentMood = saved ? saved.mood : '';
  document.getElementById('moodNote').value = saved ? (saved.note || '') : '';
  document.getElementById('moodTip').textContent = saved
    ? (isToday ? '' : dayLabelText(key) + '｜') + saved.mood + '｜' + (saved.note || moodTips[saved.mood] || '')
    : (isToday ? '选择今天的心情后' : '选择' + dayLabelText(key) + '的心情后') + '，这里会给出对应的小贴士。';

  const saveBtn = document.getElementById('saveMood');
  if (saveBtn) saveBtn.textContent = isToday ? '保存今日心情' : '保存这一天的心情';
}

function renderMoodToday() {
  renderMoodForDate(moodDateValue());
}

// 心情记录日期：默认今天，可切换到前几日补记
const moodDateInput = document.getElementById('moodDate');
if (moodDateInput) {
  const moodToday = toISODate(new Date());
  moodDateInput.max = moodToday;
  moodDateInput.value = moodToday;
  moodDateInput.addEventListener('change', function () {
    if (!moodDateInput.value || moodDateInput.value > moodToday) moodDateInput.value = moodToday;
    renderMoodForDate(moodDateInput.value);
  });
}

renderMoodToday();

// 一周心情记录：每天一张卡片，用表情包展示心情
function renderMoodWeek() {
  const box = document.getElementById('moodWeek');
  if (!box) return;

  const today = new Date();
  const todayKey = toISODate(today);
  const start = addDays(today, -6); // 与其它模块一致：近 7 天，今天在最后，不展示未来日期
  const log = loadData('moodLog', {});
  box.innerHTML = '';

  for (let index = 0; index < 7; index++) {
    const day = addDays(start, index);
    const key = toISODate(day);
    const entry = log[key];

    const item = document.createElement('div');
    item.className = 'day' + (key === todayKey ? ' selected' : '');
    item.innerHTML =
      '<span class="emoji">' + (entry ? moodEmojiOf(entry.mood) : '') + '</span>' +
      '<span class="mood-label">' + (entry ? entry.mood : '未记录') + '</span>' +
      '<span class="date">' + (key === todayKey ? '今天' : (day.getMonth() + 1) + '/' + day.getDate()) + '</span>';
    item.title = entry ? (entry.mood + (entry.note ? '：' + entry.note : '')) : '未记录';

    item.addEventListener('click', function () {
      if (!entry) {
        showToast('这一天还没有心情记录');
        return;
      }
      document.getElementById('moodTip').textContent =
        (day.getMonth() + 1) + ' 月 ' + day.getDate() + ' 日｜' + entry.mood +
        (entry.note ? '：' + entry.note : '');
    });

    box.appendChild(item);
  }
}

// ---------- 饮食活动水平：选择后立即重算目标 ----------
const dietActivity = document.getElementById('dietActivity');

// 把已保存的活动水平写回下拉框（登录同步完成后也会调用）
function applyDietActivity() {
  const select = document.getElementById('dietActivity');
  const value = loadData('dietActivity', null);
  if (!select || value === null || value === undefined || value === '') return;

  const text = String(value);
  const options = Array.from(select.options);
  const exact = options.find(function (option) {
    return option.value === text;
  });
  if (exact) {
    select.value = text;
    return;
  }

  // 兼容旧数据被四舍五入（如 1.55 存成 1.6）：按数值找最接近的选项
  const number = parseFloat(value);
  if (isNaN(number)) return;
  let best = null;
  options.forEach(function (option) {
    const optionValue = parseFloat(option.value);
    if (isNaN(optionValue)) return;
    if (!best || Math.abs(optionValue - number) < Math.abs(parseFloat(best.value) - number)) {
      best = option;
    }
  });
  if (best) {
    select.value = best.value;
    saveData('dietActivity', parseFloat(best.value));
  }
}

applyDietActivity();

dietActivity.addEventListener('change', function () {
  saveData('dietActivity', parseFloat(dietActivity.value));
  refreshDietViews();
});

// ---------- 科普资讯：点击卡片查看正文 ----------
const newsArticles = {
  diet: {
    title: '如何科学搭配三餐饮食？',
    cat: '饮食营养', color: 'green', icon: 'i-fork',
    desc: '合理的饮食搭配不仅能提供充足的能量，还能帮助预防慢性疾病，让身体保持良好状态。',
    keywords: ['饮食', '三餐', '营养', '膳食', '搭配', '吃什么', '蛋白质', '蔬菜', '水果', '主食', '减脂餐', '外卖'],
    html: '<p>《中国居民膳食指南》建议，每天的食物应尽量覆盖谷薯类、蔬菜水果、畜禽鱼蛋奶和豆类四大类，平均每天摄入 12 种以上食物，每周 25 种以上。</p>' +
      '<h4>一、三餐怎么分配</h4>' +
      '<p>早餐占全天能量的 25%-30%，午餐 30%-40%，晚餐 30%-35%。早餐建议包含主食 + 蛋白质 + 蔬果，例如燕麦牛奶配一个鸡蛋和半个苹果。</p>' +
      '<h4>二、餐盘比例</h4>' +
      '<ul><li>一半是蔬菜和水果，深色蔬菜应占蔬菜总量的一半</li>' +
      '<li>四分之一是主食，优先选择全谷物、杂豆和薯类</li>' +
      '<li>四分之一是优质蛋白，鱼、禽、蛋、瘦肉、豆制品轮换</li></ul>' +
      '<h4>三、几个容易忽略的细节</h4>' +
      '<p>每天食盐不超过 5g，烹调油 25-30g，添加糖最好控制在 25g 以内。喝水 1500-1700ml，少喝含糖饮料。进食顺序上先吃蔬菜、再吃蛋白质、最后吃主食，有助于平稳餐后血糖。</p>' +
      '<p class="note">以上为一般人群的健康建议。若有慢性疾病或特殊饮食需求，请遵医嘱或咨询注册营养师。</p>'
  },
  stretch: {
    title: '久坐族的5分钟拉伸指南',
    cat: '运动指南', color: 'blue', icon: 'i-dumbbell',
    desc: '长时间面对电脑工作，肩颈酸痛？这几个动作帮你缓解疲劳，恢复身体活力。',
    keywords: ['拉伸', '久坐', '肩颈', '颈椎', '腰背', '腰痛', '放松', '运动', '僵硬', '驼背', '工位'],
    html: '<p>连续久坐超过 60 分钟，肩颈和腰背的肌肉会持续处于紧张状态。每坐 45-60 分钟起身活动 3-5 分钟，比一次性长时间拉伸更有效。</p>' +
      '<h4>动作一：颈部侧屈（每侧 20 秒）</h4>' +
      '<p>坐直，右手轻扶头部左侧，缓慢向右侧倾斜，感受左侧颈部拉伸，不要耸肩，保持均匀呼吸后换另一侧。</p>' +
      '<h4>动作二：肩胛后缩（15 次）</h4>' +
      '<p>双臂自然下垂，肩胛骨向后向下收紧，像把两侧肩胛骨夹在一起，保持 2 秒再放松，可改善圆肩驼背。</p>' +
      '<h4>动作三：胸椎伸展（10 次）</h4>' +
      '<p>双手交叉抱头，手肘打开，缓慢向后仰 10-15 度，感受胸椎伸展，避免腰部代偿。</p>' +
      '<h4>动作四：站立体前屈（30 秒）</h4>' +
      '<p>双脚与髋同宽，膝盖微屈，身体缓慢前屈，双手自然下垂，放松腰背。起身时要慢，避免头晕。</p>' +
      '<p class="note">拉伸以轻微牵拉感为宜，出现明显疼痛应立即停止。有颈椎、腰椎疾病者请先咨询医生。</p>'
  },
  sleep: {
    title: '为什么你总是睡不够？',
    cat: '睡眠健康', color: 'purple', icon: 'i-moon',
    desc: '了解深度睡眠的重要性，以及如何通过改善卧室环境提升睡眠质量，找回好状态。',
    keywords: ['睡眠', '失眠', '睡不着', '睡不好', '熬夜', '早醒', '深睡', '打鼾', '作息', '多梦', '困', '疲劳'],
    html: '<p>成年人建议每晚睡 7-9 小时，但“睡够时长”并不等于“睡得好”。一整夜会经历 4-6 个睡眠周期，每个周期包含浅睡、深睡和快速眼动睡眠。</p>' +
      '<h4>深睡决定恢复质量</h4>' +
      '<p>深睡阶段身体修复组织、分泌生长激素、巩固免疫记忆。频繁被打断、睡前饮酒、卧室过亮或过热，都会压缩深睡时间。</p>' +
      '<h4>四个可执行的改善方法</h4>' +
      '<ul><li>固定起床时间，比固定入睡时间更容易坚持</li>' +
      '<li>睡前一小时调暗灯光，减少手机等强光刺激</li>' +
      '<li>卧室温度保持在 18-22℃，保持安静与遮光</li>' +
      '<li>下午三点后避免咖啡、浓茶，睡前避免大量进食和饮酒</li></ul>' +
      '<h4>什么时候需要就医</h4>' +
      '<p>如果每周至少 3 晚入睡困难或早醒，持续 3 个月以上，或伴随明显打鼾、呼吸暂停、白天嗜睡，建议到睡眠专科就诊。</p>' +
      '<p class="note">本页内容为健康科普，不能替代医生的诊断与治疗。</p>'
  },
  bp: {
    title: '血压血糖，家庭自测怎么做才准？',
    cat: '慢病管理', color: 'green', icon: 'i-heart',
    desc: '测压姿势、测量时间、记录方式都会影响结果，掌握几个细节让数据更可信。',
    keywords: ['血压', '血糖', '高血压', '糖尿病', '测量', '自测', '体检', '指标', '血压计', '空腹'],
    html: '<p>家庭自测能反映日常状态，比诊室单次测量更有参考价值。建议固定在早晨起床后 1 小时内、排尿后、早餐和服药前测量。</p>' +
      '<h4>测血压的四个要点</h4>' +
      '<ul><li>测量前安静坐 5 分钟，不说话、不翘腿</li>' +
      '<li>袖带与心脏同高，手臂平放在桌面上</li>' +
      '<li>每次测 2-3 遍，间隔 1 分钟，取平均值</li>' +
      '<li>连续记录 7 天，去掉第一天，取后 6 天平均值</li></ul>' +
      '<p>家庭血压一般以低于 135/85 mmHg 为参考标准，具体目标应遵医嘱。</p>' +
      '<h4>测血糖的注意事项</h4>' +
      '<p>空腹血糖需空腹 8-10 小时；餐后 2 小时血糖从吃第一口饭开始计时。采血前用温水洗手并擦干，不要用力挤压指尖，以免组织液稀释血液影响结果。</p>' +
      '<h4>记录比单次数值更重要</h4>' +
      '<p>把日期、时间、数值和当时的状态（是否运动、是否服药）一起记录，复诊时医生才能判断趋势。若出现血压持续高于 180/110 mmHg，或血糖低于 3.9 mmol/L 伴心慌出汗，应及时就医。</p>' +
      '<p class="note">以上为健康科普内容，用药与治疗请遵循医生意见。</p>'
  },
  weightloss: {
    title: '想减脂，先搞清楚这三件事',
    cat: '体重管理', color: 'orange', icon: 'i-flame',
    desc: '减重不是饿肚子：热量缺口、蛋白质和力量训练才是关键，别让体重秤骗了你。',
    keywords: ['减肥', '减脂', '瘦身', '体重', '掉秤', '热量', '卡路里', '基础代谢', '平台期', '节食', '轻断食', '燃脂', '体脂', '碳水', '减重'],
    html: '<p>减脂的核心只有一个：让消耗长期大于摄入。但“吃少一点”不等于“饿着”，过度节食会让基础代谢下降、肌肉流失，体重反弹往往更快。</p>' +
      '<h4>一、热量缺口别开太大</h4>' +
      '<p>每天 300-500 千卡的热量缺口比较可持续，对应每周减重约 0.3-0.5 公斤。缺口过大容易疲劳、掉发、月经紊乱，也很难坚持。</p>' +
      '<h4>二、蛋白质吃够</h4>' +
      '<p>减脂期每公斤体重建议摄入 1.2-1.6 克蛋白质，优先选择鸡蛋、鱼虾、瘦肉、豆制品和低脂奶。蛋白质饱腹感强，还能减少肌肉流失。</p>' +
      '<h4>三、别只看体重秤</h4>' +
      '<p>力量训练会让肌肉增加、脂肪减少，体重可能不变但围度变小。建议同时记录腰围、体脂率，以及同样强度运动时的心率变化。</p>' +
      '<p class="note">有基础疾病、正在服药或处于孕期，请先咨询医生再调整饮食与运动方案。</p>'
  },
  breakfast: {
    title: '不吃早餐，真的会胖吗？',
    cat: '饮食营养', color: 'green', icon: 'i-clock',
    desc: '早餐吃与不吃，关键看全天总热量和食物质量，别再被“必须吃早餐”绑住。',
    keywords: ['早餐', '早饭', '不吃早餐', '空腹', '早上', '牛奶', '鸡蛋', '燕麦', '豆浆', '主食', 'brunch'],
    html: '<p>“不吃早餐一定变胖”并不严谨。研究发现，真正影响体重的是全天的总热量和食物质量，而不是早餐这一顿本身。</p>' +
      '<h4>不吃早餐的常见代价</h4>' +
      '<p>跳过早餐的人容易在午餐、晚餐吃得更多，或靠高糖零食续命，血糖波动大、注意力下降。如果你不吃早餐但全天饮食均衡，影响并不大。</p>' +
      '<h4>一份合格早餐长什么样</h4>' +
      '<p>主食 + 蛋白质 + 蔬果的组合最稳：例如燕麦牛奶配鸡蛋和半个苹果，或全麦面包夹鸡胸肉配一杯无糖豆浆。避免油条、甜面包加含糖饮料的组合。</p>' +
      '<p class="note">胃病患者、青少年、孕期女性和重体力劳动者，建议规律吃早餐，不要长时间空腹。</p>'
  },
  water: {
    title: '每天 8 杯水，到底该怎么喝？',
    cat: '生活习惯', color: 'blue', icon: 'i-droplet',
    desc: '喝水没有统一公式，看尿色比数杯数更靠谱，运动、天热要额外补。',
    keywords: ['喝水', '饮水', '水', '脱水', '饮料', '奶茶', '咖啡', '尿黄', '口渴', '水肿', '每天八杯水'],
    html: '<p>“每天 8 杯水”只是一个便于记忆的说法，实际需求因人而异。一般成年人每天饮水 1500-1700 毫升，天热、运动、出汗多时要相应增加。</p>' +
      '<h4>用尿色判断更直观</h4>' +
      '<p>淡黄色接近透明说明水分充足；颜色偏深像浓茶，通常提示需要补水。不要等到口渴才喝，口渴时身体已经轻度缺水。</p>' +
      '<h4>少量多次，别一次猛灌</h4>' +
      '<p>每次 150-200 毫升，分散在全天。晨起一杯温水，运动前后各补一次。剧烈运动大量出汗时，可适当补充含电解质的饮品。</p>' +
      '<h4>这些“水”要算进去</h4>' +
      '<p>茶、咖啡、汤、牛奶都能补水，但含糖饮料和奶茶会额外带来糖与热量。心肾功能不全、需要限水的人群，饮水量应遵医嘱。</p>' +
      '<p class="note">出现明显水肿、少尿或持续口渴，建议及时就医检查。</p>'
  },
  cervical: {
    title: '低头玩手机，颈椎在替你负重',
    cat: '骨骼关节', color: 'purple', icon: 'i-yoga',
    desc: '头越低，颈椎承受的压力越大。三个习惯帮你把颈椎从屏幕里救出来。',
    keywords: ['颈椎', '低头', '手机', '脖子', '肩颈', '头晕', '富贵包', '圆肩', '手麻', '落枕', '颈椎病'],
    html: '<p>成年人的头部约重 5 公斤。低头 15 度时颈椎承受约 12 公斤，低头 60 度时可超过 27 公斤，相当于脖子上坐了一个小孩。</p>' +
      '<h4>把屏幕抬到视线高度</h4>' +
      '<p>手机尽量举到与眼睛平齐，电脑屏幕顶部与视线齐平，减少长时间低头。每用 30-40 分钟，抬头活动 1 分钟。</p>' +
      '<h4>三个简单动作</h4>' +
      '<p>下巴微收（像做双下巴）保持 5 秒，重复 10 次；肩胛骨向后向下夹紧 5 秒，重复 10 次；靠墙站立，后脑勺、肩胛、臀部贴墙 1 分钟。</p>' +
      '<h4>这些信号要就医</h4>' +
      '<p>手臂持续麻木、力量下降、走路发飘，或伴随剧烈头痛、眩晕，可能不只是肌肉疲劳，应尽快到骨科或康复科就诊。</p>' +
      '<p class="note">按摩、正骨需谨慎，急性疼痛期不要盲目大力扳动颈部。</p>'
  },
  eyes: {
    title: '盯屏幕一小时，眼睛经历了什么？',
    cat: '用眼健康', color: 'blue', icon: 'i-search',
    desc: '眨眼次数骤减、泪膜蒸发加快，干涩和酸胀就是这样来的。',
    keywords: ['眼睛', '护眼', '近视', '干眼', '视疲劳', '屏幕', '蓝光', '眼药水', '酸胀', '视力', '眨眼'],
    html: '<p>正常情况下人每分钟眨眼 15-20 次，专注看屏幕时会降到 5-7 次。眨眼减少会让泪膜蒸发加快，出现干涩、异物感和酸胀。</p>' +
      '<h4>20-20-20 法则</h4>' +
      '<p>每看屏幕 20 分钟，抬头看 6 米外的地方 20 秒。这个动作能让睫状肌放松，缓解调节痉挛引起的视疲劳。</p>' +
      '<h4>环境与习惯</h4>' +
      '<p>屏幕亮度与环境光接近，避免关灯玩手机；屏幕略低于视线 10-15 度；有意识地完整眨眼。空调房里可用加湿器缓解干燥。</p>' +
      '<h4>眼药水别乱滴</h4>' +
      '<p>含防腐剂的人工泪液不宜长期高频使用；宣称“去红血丝”的滴眼液可能掩盖炎症。持续干涩、视力波动应到眼科检查。</p>' +
      '<p class="note">儿童青少年每天户外活动 2 小时，是目前证据较充分的近视预防措施。</p>'
  },
  mood: {
    title: '压力大时，身体会发生什么？',
    cat: '心理健康', color: 'purple', icon: 'i-smile',
    desc: '心跳加快、睡不好、胃口变化，都是压力激素在起作用。学会给身体“踩刹车”。',
    keywords: ['压力', '焦虑', '情绪', '紧张', '抑郁', '心情', '放松', '冥想', '深呼吸', '失眠', '烦躁', '内耗'],
    html: '<p>压力来时，身体会分泌肾上腺素和皮质醇，让心跳加快、肌肉紧绷、注意力集中。短期这是保护机制，长期持续则会拖垮睡眠和免疫。</p>' +
      '<h4>身体会给出的信号</h4>' +
      '<p>入睡困难、早醒、心慌、胃口明显变化、肩颈僵硬、容易感冒、注意力下降，都可能是长期压力的表现。</p>' +
      '<h4>三个可操作的减压方式</h4>' +
      '<p>4-7-8 呼吸：吸气 4 秒、屏息 7 秒、呼气 8 秒，重复 4 轮；每天 10 分钟快走或拉伸；把担心的事写下来，区分“能改变的”和“改变不了的”。</p>' +
      '<h4>什么时候需要求助</h4>' +
      '<p>情绪低落持续两周以上、对原本喜欢的事失去兴趣、影响工作和人际，或出现伤害自己的念头，请及时寻求心理科或专业心理咨询帮助。</p>' +
      '<p class="note">心理问题和感冒一样需要治疗，求助不是软弱。</p>'
  },
  immunity: {
    title: '免疫力不是越高越好',
    cat: '免疫健康', color: 'green', icon: 'i-leaf',
    desc: '真正有用的是免疫平衡：睡够、吃好、动起来，比乱补保健品靠谱。',
    keywords: ['免疫', '抵抗力', '感冒', '维生素', '发烧', '疫苗', '熬夜', '营养', '保健品', '过敏', '发炎'],
    html: '<p>免疫系统需要的是“平衡”，而不是“越强越好”。免疫力过强可能带来过敏、自身免疫病，盲目进补反而添乱。</p>' +
      '<h4>最有效的四件事</h4>' +
      '<p>睡够 7-9 小时；每天吃够蔬菜水果和优质蛋白；每周 150 分钟中等强度运动；按程序接种疫苗。这四件事的证据远比保健品充分。</p>' +
      '<h4>关于维生素</h4>' +
      '<p>饮食均衡的人通常不需要额外补充。长期缺乏、特殊人群可在医生指导下补充，过量脂溶性维生素反而有中毒风险。</p>' +
      '<h4>感冒了怎么办</h4>' +
      '<p>多数普通感冒 7-10 天自愈，注意休息和补水即可。持续高热超过 3 天、呼吸困难、精神差，应及时就医。</p>' +
      '<p class="note">不要用“提高免疫力”作为长期服用保健品的理由。</p>'
  },
  women: {
    title: '经期不适，哪些情况该就医？',
    cat: '女性健康', color: 'pink', icon: 'i-female',
    desc: '痛经、周期紊乱、经量异常，哪些可以观察，哪些不能拖。',
    keywords: ['经期', '月经', '痛经', '例假', '周期', '经量', '女性', '妇科', '红糖水', '止痛药', '推迟', '闭经'],
    html: '<p>轻度痛经、乳房胀痛、情绪波动属于常见经期反应，可通过热敷、规律作息和适度运动缓解。</p>' +
      '<h4>痛经可以吃止痛药</h4>' +
      '<p>原发性痛经与前列腺素分泌有关，布洛芬等药物在疼痛开始时按说明服用效果更好。担心伤胃可以饭后服用，不必硬扛。</p>' +
      '<h4>这些情况建议就诊</h4>' +
      '<p>痛经逐年加重、止痛药无效；周期短于 21 天或长于 35 天；经量突然明显增多或减少；非经期出血；闭经超过 3 个月。这些可能提示子宫内膜异位症、多囊卵巢等问题。</p>' +
      '<h4>红糖水更多是心理安慰</h4>' +
      '<p>热饮能让人舒服，但红糖本质是糖，缓解痛经的证据有限。经期注意保暖、少熬夜，比喝糖水更有意义。</p>' +
      '<p class="note">以上为科普内容，具体诊断与用药请咨询妇科医生。</p>'
  }
};

const newsMask = document.getElementById('newsMask');

// 点击卡片：在新标签页打开浏览器搜索，查看该主题的完整内容
function openArticleInBrowser(title) {
  const url = 'https://www.baidu.com/s?wd=' + encodeURIComponent(title + ' 健康科普');
  window.open(url, '_blank', 'noopener');
}

// ---------- 科普资讯：卡片渲染、搜索排序与换一批 ----------
const newsGrid = document.querySelector('.news-grid');
const newsSearch = document.getElementById('newsSearch');
const newsCount = document.getElementById('newsCount');
let newsOrder = Object.keys(newsArticles);

// 中文按 2 字切分，这样「睡眠不好」也能命中「睡眠」相关文章
function newsTokens(keyword) {
  if (!keyword) return [];
  if (keyword.length < 2) return [keyword];
  const tokens = [keyword];
  for (let i = 0; i < keyword.length - 1; i++) {
    tokens.push(keyword.slice(i, i + 2));
  }
  return tokens;
}

function escapeNewsHtml(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function highlightNewsTitle(title, keyword) {
  const token = newsTokens(keyword)
    .filter(function (item) { return item.length >= 2; })
    .sort(function (a, b) { return b.length - a.length; })[0];
  const index = token ? title.indexOf(token) : -1;
  if (index === -1) return escapeNewsHtml(title);
  return escapeNewsHtml(title.slice(0, index)) +
    '<mark>' + escapeNewsHtml(token) + '</mark>' +
    escapeNewsHtml(title.slice(index + token.length));
}

// 标题命中权重最高，其次关键词、摘要、正文
function scoreArticle(article, keyword) {
  if (!keyword) return 1;
  const title = article.title.toLowerCase();
  const keys = (article.keywords || []).join(' ').toLowerCase();
  const desc = (article.desc || '').toLowerCase();
  const body = (article.html || '').toLowerCase();

  return newsTokens(keyword).reduce(function (score, token) {
    if (!token) return score;
    if (title.indexOf(token) !== -1) score += 8;
    if (keys.indexOf(token) !== -1) score += 5;
    if (desc.indexOf(token) !== -1) score += 3;
    if (body.indexOf(token) !== -1) score += 1;
    return score;
  }, 0);
}

// 封面池：每个主题在几张真实照片之间轮换，点「换一批」整页换图
const NEWS_COVER_POOL = {
  diet: ['diet', 'breakfast', 'immunity'],
  breakfast: ['breakfast', 'diet', 'water'],
  sleep: ['sleep', 'mood', 'women'],
  bp: ['bp', 'cervical', 'weightloss'],
  weightloss: ['weightloss', 'stretch', 'cervical'],
  water: ['water', 'immunity', 'breakfast'],
  stretch: ['stretch', 'cervical', 'weightloss'],
  cervical: ['cervical', 'stretch', 'eyes'],
  eyes: ['eyes', 'cervical', 'mood'],
  mood: ['mood', 'sleep', 'women'],
  immunity: ['immunity', 'diet', 'water'],
  women: ['women', 'mood', 'sleep']
};

const NEWS_COVER_ALL = ['diet', 'breakfast', 'water', 'sleep', 'mood', 'women',
  'bp', 'weightloss', 'cervical', 'stretch', 'eyes', 'immunity'];

let newsCoverSeed = Math.floor(Math.random() * NEWS_COVER_ALL.length);
// 本次渲染已经用掉的封面，保证同一页里不出现重复图片
let newsCoverUsed = [];

function newsCoverReset() {
  newsCoverUsed = [];
}

// 按主题取一组候选（用 seed 轮换顺序，点「换一批」时整体换一套）
function newsCoverPool(key) {
  const pool = NEWS_COVER_POOL[key] || [key];
  const offset = (newsCoverSeed + key.charCodeAt(0) + key.length) % pool.length;
  return pool.map(function (_, index) {
    return pool[(offset + index) % pool.length];
  });
}

function newsCoverPick(key) {
  const candidates = newsCoverPool(key);
  let pick = '';

  candidates.some(function (name) {
    if (newsCoverUsed.indexOf(name) !== -1) return false;
    pick = name;
    return true;
  });

  // 主题图都被占用了，就从整张图库里补一张没用过的
  if (!pick) {
    for (let index = 0; index < NEWS_COVER_ALL.length; index++) {
      const name = NEWS_COVER_ALL[(newsCoverSeed + index) % NEWS_COVER_ALL.length];
      if (newsCoverUsed.indexOf(name) === -1) { pick = name; break; }
    }
  }
  // 卡片多于 12 张时只能复用
  if (!pick) pick = candidates[0] || NEWS_COVER_ALL[0];

  newsCoverUsed.push(pick);
  return pick;
}

// 科普封面：本站封面图，加载完成才淡入；加载慢或失败时保留下面的渐变图标
function newsCoverHtml(key, color, icon, title) {
  const pick = newsCoverPick(key);
  const altText = String(title || '科普资讯封面').replace(/["<>&]/g, '');
  return '<div class="news-img ' + color + '">' +
    '<svg class="icon"><use href="#' + icon + '"/></svg>' +
    '<img src="/assets/news/' + pick + '.jpg" alt="' + altText + '" loading="lazy" ' +
    'onload="this.classList.add(\'is-ready\')" onerror="this.remove()">' +
    '</div>';
}

function newsCardHtml(key, article, keyword) {
  return '<article class="news-card" data-article="' + key + '">' +
    newsCoverHtml(key, article.color, article.icon, article.title) +
    '<div class="news-body">' +
      '<div class="news-cat ' + article.color + '">' + escapeNewsHtml(article.cat) + '</div>' +
      '<div class="news-title">' + highlightNewsTitle(article.title, keyword) + '</div>' +
      '<p class="news-desc">' + escapeNewsHtml(article.desc) + '</p>' +
      '<button type="button" class="read-more">在浏览器中查看全文 ›</button>' +
      '<span class="news-quick" data-quick="1">速读摘要</span>' +
    '</div></article>';
}

function filterNews() {
  const raw = newsSearch.value.trim();
  const keyword = raw.toLowerCase();

  // 切回内置科普内容时，隐藏网络资讯的来源提示
  const hint = document.getElementById('newsSourceHint');
  if (hint) hint.hidden = true;

  const list = Object.keys(newsArticles).map(function (key) {
    return { key: key, article: newsArticles[key], score: scoreArticle(newsArticles[key], keyword) };
  });

  let visible = list.filter(function (item) { return item.score > 0; });
  let recommend = false;

  // 一条都匹配不上时，全部作为推荐展示，避免出现空白
  if (keyword && visible.length === 0) {
    visible = list;
    recommend = true;
  }

  if (keyword) {
    visible.sort(function (a, b) { return b.score - a.score; });
  } else {
    visible.sort(function (a, b) { return newsOrder.indexOf(a.key) - newsOrder.indexOf(b.key); });
  }

  newsCoverReset();
  newsGrid.innerHTML = visible.map(function (item) {
    return newsCardHtml(item.key, item.article, keyword);
  }).join('');

  newsCount.textContent = !keyword ? '' :
    (recommend ? '未找到「' + raw + '」，为你推荐 ' + visible.length + ' 条' : '找到 ' + visible.length + ' 条');
  document.getElementById('newsEmpty').hidden = true;

  document.querySelectorAll('.news-tag').forEach(function (tag) {
    tag.classList.toggle('active', tag.dataset.tag === raw);
  });
}

// 点击卡片：普通点击跳百度看全文，点「速读摘要」在站内弹窗看
newsGrid.addEventListener('click', function (event) {
  const card = event.target.closest('.news-card');
  if (!card) return;
  const article = newsArticles[card.dataset.article];
  if (!article) return;

  if (event.target.closest('.news-quick')) {
    event.stopPropagation();
    document.getElementById('newsTitle').textContent = article.title;
    document.getElementById('newsBody').innerHTML = article.html;
    openMask(newsMask);
    return;
  }

  openArticleInBrowser(article.title);
});

// 热门词一键搜索
document.querySelectorAll('.news-tag').forEach(function (tag) {
  tag.addEventListener('click', function () {
    newsSearch.value = tag.dataset.tag;
    filterNews();
  });
});

newsSearch.addEventListener('input', filterNews);

// ---------- 刷新：从后端拉取真实新闻（必应资讯），失败时回退内置内容 ----------
const NEWS_SEEN_KEY = 'newsSeen';
const newsSourceHint = document.getElementById('newsSourceHint');
let liveNews = [];

function seenNewsLinks() {
  const list = loadData(NEWS_SEEN_KEY, []);
  return Array.isArray(list) ? list : [];
}

function markNewsSeen(link) {
  if (!link) return;
  const list = seenNewsLinks();
  if (list.indexOf(link) !== -1) return;
  list.unshift(link);
  saveData(NEWS_SEEN_KEY, list.slice(0, 200));
}

function formatNewsTime(raw) {
  const text = String(raw || '').trim();
  if (!text) return '刚刚更新';
  const date = new Date(text);
  if (!isNaN(date.getTime())) {
    const pad = function (value) { return String(value).padStart(2, '0'); };
    return (date.getMonth() + 1) + '-' + pad(date.getDate()) + ' ' +
      pad(date.getHours()) + ':' + pad(date.getMinutes());
  }
  return text.slice(0, 10);
}

function liveNewsCardHtml(item, index) {
  const colors = ['green', 'blue', 'purple', 'orange', 'pink'];
  const icons = ['i-book', 'i-heart', 'i-pulse', 'i-leaf', 'i-activity'];
  const color = colors[index % colors.length];
  const icon = icons[index % icons.length];
  const time = formatNewsTime(item.published);
  const summary = item.summary || '点击查看这条资讯的完整内容。';

  const themes = ['diet', 'sleep', 'stretch', 'bp', 'mood', 'weightloss',
    'water', 'cervical', 'eyes', 'breakfast', 'immunity', 'women'];
  return '<article class="news-card live" data-link="' + escapeNewsHtml(item.link) + '">' +
    newsCoverHtml(themes[index % themes.length], color, icon) +
    '<div class="news-body">' +
      '<div class="news-cat ' + color + '">' + escapeNewsHtml(item.source || '健康资讯') + '</div>' +
      '<div class="news-title">' + escapeNewsHtml(item.title) + '</div>' +
      '<p class="news-desc">' + escapeNewsHtml(summary) + '</p>' +
      '<div class="news-live-meta"><span class="src">网络资讯</span><span>' +
        escapeNewsHtml(time || '刚刚更新') + '</span></div>' +
      '<button type="button" class="read-more">在浏览器中查看全文 ›</button>' +
    '</div></article>';
}

// 拉取真实资讯：过滤已经看过的链接，保证每次刷新都是新内容
async function refreshLiveNews(manual) {
  if (!serverMode) {
    if (manual) showToast('本地演示版没有后端，无法获取网络资讯');
    return false;
  }

  const keyword = newsSearch.value.trim() || '健康';
  const button = document.getElementById('newsRefresh');
  button.disabled = true;

  try {
    const result = await api('/api/news?limit=30&q=' + encodeURIComponent(keyword));
    const items = (result.ok && result.data.items) ? result.data.items : [];
    if (!items.length) {
      if (manual) showToast('暂时没有获取到网络资讯，已保留当前内容');
      return false;
    }

    const seen = seenNewsLinks();
    const fresh = items.filter(function (item) {
      return item.link && seen.indexOf(item.link) === -1;
    });
    const picked = (fresh.length ? fresh : items).slice(0, 12);

    liveNews = picked;
    newsCoverReset();
    newsGrid.innerHTML = picked.map(liveNewsCardHtml).join('');
    newsCount.textContent = '为你找到 ' + picked.length + ' 条最新资讯';
    document.getElementById('newsEmpty').hidden = true;
    newsSourceHint.hidden = false;
    newsSourceHint.innerHTML = '来源：<b>中国新闻网 / 人民网健康</b>　关键词「' + escapeNewsHtml(keyword) +
      '」，点击卡片可在浏览器查看原文。';
    picked.forEach(function (item) { markNewsSeen(item.link); });

    if (manual) showToast(fresh.length ? '已更新 ' + picked.length + ' 条新资讯' : '暂时没有更新的资讯，已展示最新内容');
    return true;
  } catch (error) {
    if (manual) showToast('网络资讯获取失败，已保留当前内容');
    return false;
  } finally {
    button.disabled = false;
  }
}

document.getElementById('newsRefresh').addEventListener('click', function () {
  newsCoverSeed += 1;
  refreshLiveNews(true).then(function (ok) {
    // 没取到网络资讯时，至少把内置卡片的封面换一批
    if (!ok) filterNews();
  });
});

// 点击网络资讯卡片：直接打开原文
newsGrid.addEventListener('click', function (event) {
  const live = event.target.closest('.news-card.live');
  if (!live) return;
  const link = live.dataset.link;
  if (link) window.open(link, '_blank', 'noopener');
});

// 进入资讯页后自动尝试拉取一次真实资讯（失败保持内置内容）
document.querySelectorAll('.side-nav button').forEach(function (button) {
  if (button.dataset.page !== 'news') return;
  button.addEventListener('click', function () {
    if (!liveNews.length) refreshLiveNews(false);
  });
});

document.getElementById('newsClose').addEventListener('click', function () {
  closeMask(newsMask);
});

newsMask.addEventListener('click', function (event) {
  if (event.target === newsMask) closeMask(newsMask);
});

// ---------- 新功能初始化 ----------
// 放到下一个任务里执行：先让登录页完成首屏绘制，再做图表与列表这些重活
setTimeout(function () {
  filterNews();
  loadProfileView();
  renderVitalRanges();
  renderMealLog();
  refreshDietViews();
  fillSportInputs();
  renderExercise('today');
  renderWeightChart();
  renderMoodWeek();
  renderWeekPanel();
}, 0);

// 从后端取回数据后，把内存变量与页面重新同步成最新状态
function resetSupplementDates() {
  const today = toISODate(new Date());
  ['mealDate', 'moodDate', 'sdDate', 'feelDate'].forEach(function (id) {
    const input = document.getElementById(id);
    if (input) {
      input.max = today;
      input.value = today;
    }
  });
}

function refreshAllViews() {
  resetSupplementDates();
  weightHistory = loadData('weightHistory', []);
  mealLog = loadData('mealLog', []);
  reminders = loadData('reminders', []);
  quickReminders = loadData('quickReminders', []);
  familyMembers = loadData('familyMembers', []);
  familyRecords = loadData('familyRecords', []);

  const sport = loadData('sport', null);
  if (sport && sport.goal) {
    reloadSportState();
  }

  const bp = loadData('bp', null);
  const bpBox = document.getElementById('bpValue');
  if (bpBox && bp && bp.systolic && bp.diastolic) {
    bpBox.textContent = bp.systolic + '/' + bp.diastolic;
  }
  const glucose = loadData('glucose', null);
  const glucoseBox = document.getElementById('glucoseValue');
  if (glucoseBox && glucose) {
    glucoseBox.textContent = Number(glucose).toFixed(1);
  }
  applyDietActivity();

  loadProfileView();
  renderVitalRanges();
  renderMealLog();
  refreshDietViews();
  fillSportInputs();
  renderExercise('today');
  renderWeightChart();
  renderMoodToday();
  renderMoodWeek();
  renderWeekPanel();
  renderReminders();
  renderQuickReminders();
  renderFamilyMembers();
  renderMemberOptions();
  applyFemaleProfile(loadData('femaleProfile', null));
  renderCycle();
  renderSleepToday();
  renderSleepWeek();
  restoreBeautyPlan();
  restoreReport();
  applyGenderView();
  renderPeriodFeel();
  updateAdminEntry();
}

// 恢复最近一份体检报告的指标
function restoreReport() {
  const list = loadData('reports', []);
  if (!list || !list.length) return;
  const latest = list.slice().sort(function (a, b) {
    return String(a.date) < String(b.date) ? 1 : -1;
  })[0];
  renderReportResult(latest, latest.date);
  reportStatus.className = 'upload-status';
  reportStatus.textContent = '显示上次同步的体检指标（报告日期见下方）';
}

/* ==========================================================
   页面启动：尝试恢复已登录的会话（后端不可用时退回本地演示）
   ========================================================== */
bootAuth();

/* ==========================================================
   七、AI 健康小管家聊天
   ========================================================== */
const chat = document.getElementById('chat');
const chatBody = document.getElementById('chatBody');
const chatInput = document.getElementById('chatInput');
const assistantLog = document.getElementById('assistantLog');
const assistantInput = document.getElementById('assistantInput');

// 悬浮窗与整页共用这一份对话，保证两边看到的内容一致
const CHAT_GREETING = '你好！我是你的专属 AI 健康助理。请问今天有什么我可以帮你的？关于饮食计算、运动建议或是生理期护理，都可以问我。';
let chatMessages = [];
// 当前正在聊的对话 id（null 表示还没开始，发送第一条时由服务端创建）
let currentConversationId = null;

const assistantHistoryBtn = document.getElementById('assistantHistory');
const assistantHistPanel = document.getElementById('assistantHistPanel');
const assistantHistList = document.getElementById('assistantHistList');
const assistantHistEmpty = document.getElementById('assistantHistEmpty');

function openChat() {
  chat.classList.add('open');
  document.getElementById('fabDot').style.display = 'none';
  chatInput.focus();
}

function closeChat() {
  chat.classList.remove('open');
}

function toggleChat() {
  if (chat.classList.contains('open')) {
    closeChat();
  } else {
    openChat();
  }
}

// AI 悬浮球：支持拖动，位置记在本机
const fab = document.getElementById('fab');
const FAB_POS_KEY = 'fabPos';
let fabDragging = false;

function clampFab(right, bottom) {
  const size = 58;
  return {
    right: Math.min(Math.max(right, 8), Math.max(8, window.innerWidth - size - 8)),
    bottom: Math.min(Math.max(bottom, 8), Math.max(8, window.innerHeight - size - 8))
  };
}

function placeFab(right, bottom) {
  const pos = clampFab(right, bottom);
  fab.style.right = pos.right + 'px';
  fab.style.bottom = pos.bottom + 'px';
  fab.style.left = 'auto';
  return pos;
}

(function restoreFabPosition() {
  const saved = loadData(FAB_POS_KEY, null);
  if (saved && typeof saved.right === 'number' && typeof saved.bottom === 'number') {
    placeFab(saved.right, saved.bottom);
  }
})();

window.addEventListener('resize', function () {
  if (!fab.style.right) return;
  placeFab(parseFloat(fab.style.right) || 26, parseFloat(fab.style.bottom) || 26);
});

(function enableFabDrag() {
  let start = null;

  fab.addEventListener('pointerdown', function (event) {
    if (event.button !== undefined && event.button !== 0) return;
    start = {
      x: event.clientX,
      y: event.clientY,
      right: parseFloat(getComputedStyle(fab).right) || 26,
      bottom: parseFloat(getComputedStyle(fab).bottom) || 26
    };
    fabDragging = false;
    fab.setPointerCapture(event.pointerId);
  });

  fab.addEventListener('pointermove', function (event) {
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;

    if (!fabDragging && Math.abs(dx) + Math.abs(dy) < 6) return;
    fabDragging = true;
    fab.classList.add('dragging');
    placeFab(start.right - dx, start.bottom - dy);
  });

  function endDrag() {
    if (!start) return;
    start = null;
    fab.classList.remove('dragging');
    if (!fabDragging) return;
    saveData(FAB_POS_KEY, {
      right: parseFloat(fab.style.right) || 26,
      bottom: parseFloat(fab.style.bottom) || 26
    });
    // 让随后的 click 事件不要误触发聊天窗口
    setTimeout(function () { fabDragging = false; }, 0);
  }

  fab.addEventListener('pointerup', endDrag);
  fab.addEventListener('pointercancel', endDrag);
})();

fab.addEventListener('click', function (event) {
  if (fabDragging) {
    event.preventDefault();
    return;
  }
  toggleChat();
});
document.getElementById('chatClose').addEventListener('click', closeChat);

/* ==========================================================
   语音输入：先点输入框，再点左下角按钮说话
   ========================================================== */
const voiceFab = document.getElementById('voiceFab');
const voiceFabText = document.getElementById('voiceFabText');
const chatVoiceBtn = document.getElementById('chatVoice');
const chatInputBox = document.getElementById('chatInput');
const voicePanel = document.getElementById('voicePanel');
const voiceText = document.getElementById('voiceText');
const voiceStatus = document.getElementById('voiceStatus');
const voiceOkBtn = document.getElementById('voiceOk');
let pendingVoiceAutoSend = false;   // 小管家麦克风触发时，确认后自动发送
let voiceAutoSend = false;
let voicePanelOpen = false;
let voiceErrorShown = false;
let voiceHasResult = false;         // 浏览器识别是否已经给出过文字
const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let voiceRecog = null;
let voiceTarget = null;
let lastEditable = null;

// 录音状态同时点亮左下角按钮和小管家麦克风
function setVoiceRecording(on) {
  voiceFab.classList.toggle('listening', on);
  if (chatVoiceBtn) chatVoiceBtn.classList.toggle('listening', on);
}

function setVoiceStatus(text) {
  voiceStatus.textContent = text || '';
}

// 打开面板：先看着识别结果，再决定是否填入
function openVoicePanel(statusText) {
  voicePanel.hidden = false;
  voicePanelOpen = true;
  voiceText.value = '';
  voiceHasResult = false;
  voiceErrorShown = false;
  voiceOkBtn.textContent = '✓ 填入';
  setVoiceStatus(statusText || '正在听，请说话…');
}

function closeVoicePanel() {
  voicePanel.hidden = true;
  voicePanelOpen = false;
}

// 取消：停止录音/识别，不填任何内容
function cancelVoice() {
  voiceAutoSend = false;
  if (voiceRecog) {
    try { voiceRecog.abort(); } catch (error) {}
  }
  if (recorder) releaseRecorder();
  closeVoicePanel();
  resetVoiceButton();
}

// 判断这句话是不是「让小管家去记录」的指令
function looksLikeVoiceCommand(text) {
  return /(帮我|请|给).{0,6}(记|添加)|记录|记一下|记上|新增|吃了|喝了|早餐|午餐|晚餐|加餐|运动|跑步|体重|血压|血糖|睡眠|心情/.test(text);
}

// 交给小管家：走服务端意图识别，真正写入对应记录
function sendVoiceToAssistant(text) {
  openChat();
  sendChat(text);
}

// 确认：把面板里的文字填入目标输入框（或交给小管家处理）
function fillFromVoicePanel() {
  const text = voiceText.value.trim();
  if (!text) {
    showToast('没有听到内容，请再说一次');
    return;
  }
  const target = voiceTarget;
  closeVoicePanel();
  const isNumber = target && target.type === 'number';
  const asCommand = !isNumber && (!target || looksLikeVoiceCommand(text));
  if (asCommand) {
    sendVoiceToAssistant(text);
    showToast('已交给小管家处理');
  } else {
    fillVoiceTarget(target, text);
    showToast('已填入：' + text.slice(0, 24));
    maybeAutoSendVoice(target);
  }
  resetVoiceButton();
}

document.getElementById('voiceCancel').addEventListener('click', cancelVoice);

voiceOkBtn.addEventListener('click', function () {
  // 服务器识别还在录音：先结束录音，识别结果会回到面板
  if (recorder) {
    stopRecorder(true);
    return;
  }
  fillFromVoicePanel();
});

// 小管家语音：识别完成后直接发送
function maybeAutoSendVoice(target) {
  if (!voiceAutoSend) return;
  voiceAutoSend = false;
  if (chatInputBox && target === chatInputBox) {
    const send = document.getElementById('chatSend');
    if (send) send.click();
  }
}

if (chatVoiceBtn && chatInputBox) {
  chatVoiceBtn.addEventListener('click', function () {
    if (voicePanelOpen) {
      voiceOkBtn.click();
      return;
    }
    chatInputBox.focus();
    pendingVoiceAutoSend = true;
    voiceFab.click();
  });
}

// 记住最后聚焦的可编辑输入框（密码、文件等敏感字段除外）
document.addEventListener('focusin', function (event) {
  const node = event.target;
  if (!node || !node.tagName) return;
  const tag = node.tagName.toLowerCase();
  if (tag !== 'input' && tag !== 'textarea') return;
  if (node.type === 'password' || node.type === 'file' || node.disabled || node.readOnly) return;
  // 语音面板里的输入框不作为填入目标
  if (node.closest && node.closest('#voicePanel')) return;
  lastEditable = node;
});

// 把「三十」「一百二」这类口语转换成数字，供数字输入框使用
function spokenToNumber(text) {
  const arabic = String(text).match(/\d+(\.\d+)?/);
  if (arabic) return arabic[0];

  const digits = { '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
                   '五': 5, '六': 6, '七': 7, '八': 8, '九': 9 };
  const units = { '十': 10, '百': 100, '千': 1000 };
  let total = 0;
  let current = 0;
  const chars = String(text);
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    if (Object.prototype.hasOwnProperty.call(digits, ch)) {
      current = digits[ch];
    } else if (Object.prototype.hasOwnProperty.call(units, ch)) {
      total += (current || 1) * units[ch];
      current = 0;
    }
  }
  total += current;
  return total ? String(total) : '';
}

function fillVoiceTarget(target, text) {
  const value = target.type === 'number' ? spokenToNumber(text) : text;
  if (!value) {
    showToast('没有识别到数字，请再说一次，例如「三十」');
    return;
  }
  target.value = value;
  target.dispatchEvent(new Event('input', { bubbles: true }));
  target.dispatchEvent(new Event('change', { bubbles: true }));
  target.focus();
}

function resetVoiceButton() {
  setVoiceRecording(false);
  voiceFabText.textContent = '语音输入';
}

/* ---------- 服务器语音识别（阿里云）：录音 -> 上传 -> 填字 ---------- */
let asrStatusCache = null;   // null=还没查询，true/false=服务端是否已配置
let recorder = null;
let voiceBusy = false;

function writeWavString(view, offset, text) {
  for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
}

// 合并录音片段，降采样到 16k，并编码成 WAV
function encodeWav(chunks, inputRate) {
  let length = 0;
  chunks.forEach(function (chunk) { length += chunk.length; });
  const merged = new Float32Array(length);
  let offset = 0;
  chunks.forEach(function (chunk) { merged.set(chunk, offset); offset += chunk.length; });

  const targetRate = 16000;
  const ratio = (inputRate || 48000) / targetRate;
  const outLength = Math.max(1, Math.floor(merged.length / ratio));
  const samples = new Int16Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(merged.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) { sum += merged[j]; count++; }
    let value = count ? sum / count : 0;
    value = Math.max(-1, Math.min(1, value));
    samples[i] = value < 0 ? value * 0x8000 : value * 0x7FFF;
  }

  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  writeWavString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeWavString(view, 8, 'WAVE');
  writeWavString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeWavString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  new Int16Array(buffer, 44).set(samples);
  return new Uint8Array(buffer);
}

function bytesToBase64(bytes) {
  let binary = '';
  const step = 0x8000;
  for (let i = 0; i < bytes.length; i += step) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
  }
  return btoa(binary);
}

async function fetchAsrStatus() {
  if (!serverMode) return false;
  if (asrStatusCache !== null) return asrStatusCache;
  try {
    const result = await api('/api/asr/status');
    asrStatusCache = !!(result.ok && result.data.configured);
  } catch (error) {
    asrStatusCache = false;
  }
  return asrStatusCache;
}

async function startRecorder() {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
  });
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  // iOS 上 AudioContext 默认是挂起状态，不 resume 会一直录不到声音
  if (ctx.state === 'suspended') {
    try { await ctx.resume(); } catch (error) {}
  }
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  const meter = { level: 0, lastVoice: Date.now(), start: Date.now() };
  processor.onaudioprocess = function (event) {
    const data = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(data));
    let sum = 0;
    let count = 0;
    for (let i = 0; i < data.length; i += 4) { sum += data[i] * data[i]; count++; }
    const rms = count ? Math.sqrt(sum / count) : 0;
    meter.level = Math.max(meter.level * 0.6, Math.min(1, rms * 12));
    if (rms > 0.012) meter.lastVoice = Date.now();
  };
  source.connect(processor);
  processor.connect(ctx.destination);
  recorder = {
    stream: stream, ctx: ctx, source: source, processor: processor, chunks: chunks,
    meter: meter,
    ticker: setInterval(function () {
      if (!recorder) return;
      const level = recorder.meter.level;
      const bars = level > 0.45 ? '■■■' : level > 0.15 ? '■■□' : level > 0.04 ? '■□□' : '□□□';
      const now = Date.now();
      // 说完停顿 1.5 秒自动结束，减少等待时间
      if (now - recorder.meter.lastVoice > 1500 && now - recorder.meter.start > 1200) {
        setVoiceStatus('检测到停顿，正在结束录音…');
        stopRecorder(true);
        return;
      }
      setVoiceStatus('正在录音 ' + bars + ' ｜ 说完可点 ✓，停顿 1.5 秒自动结束');
    }, 400),
    timer: setTimeout(function () { stopRecorder(true); }, 20000)
  };
  setVoiceRecording(true);
  voiceFabText.textContent = '录音中…';
}

function releaseRecorder() {
  if (!recorder) return null;
  clearTimeout(recorder.timer);
  clearInterval(recorder.ticker);
  try { recorder.processor.disconnect(); } catch (error) {}
  try { recorder.source.disconnect(); } catch (error) {}
  recorder.stream.getTracks().forEach(function (track) { track.stop(); });
  const audio = { chunks: recorder.chunks, rate: recorder.ctx.sampleRate || 48000 };
  try { recorder.ctx.close(); } catch (error) {}
  recorder = null;
  return audio;
}

async function stopRecorder(auto) {
  if (!recorder || voiceBusy) return;
  voiceBusy = true;
  const audio = releaseRecorder();
  setVoiceRecording(false);
  setVoiceStatus('识别中…');
  voiceFabText.textContent = '识别中…';

  try {
    const wav = encodeWav(audio.chunks, audio.rate);
    if (wav.length < 3200) {
      setVoiceStatus('录音太短，请再说几个字后重试');
      showToast('录音太短，请多说几个字');
      return;
    }
    const result = await api('/api/asr', {
      method: 'POST',
      body: { audio: bytesToBase64(wav), format: 'wav' }
    });
    if (!result.ok) {
      if (result.status === 503) asrStatusCache = false;
      const detail = (result.data && result.data.error) || ('HTTP ' + result.status);
      setVoiceStatus('语音识别失败：' + detail + '（可直接在框里手写）');
      showToast('语音识别失败：' + detail);
      return;
    }
    const text = String(result.data.text || '').trim();
    if (!text) {
      setVoiceStatus('没有识别到内容，请再说一次');
      showToast('没有识别到内容，请再说一次');
      return;
    }
    voiceText.value = text;
    voiceHasResult = true;
    voiceOkBtn.textContent = '✓ 填入';
    setVoiceStatus('识别完成，确认无误后点 ✓ 填入');
  } catch (error) {
    setVoiceStatus('识别失败，可直接在框里手写后点 ✓');
    showToast('语音识别失败，请检查网络后重试');
  } finally {
    voiceBusy = false;
    resetVoiceButton();
  }
}

let voiceFinalText = '';

function startBrowserRecognition() {
  if (!SpeechRecognitionCtor) return;
  voiceFinalText = '';
  try {
    voiceRecog.start();
    setVoiceRecording(true);
    setVoiceStatus('正在听，请说话…');
  } catch (error) {
    setVoiceStatus('浏览器识别启动失败，改用服务器识别…');
    startServerVoice();
  }
}

async function startServerVoice() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setVoiceStatus('当前浏览器无法录音，请直接输入文字');
    showToast('当前浏览器无法录音，请改用 Edge 或手动输入');
    return;
  }
  try {
    await startRecorder();
    setVoiceStatus('正在录音，说完点 ✓ 结束并识别');
  } catch (error) {
    const message = error && error.name === 'NotAllowedError'
      ? '麦克风权限被拒绝，请在浏览器设置里允许后重试'
      : '无法启动录音，请检查麦克风';
    setVoiceStatus(message);
    showToast(message);
    resetVoiceButton();
  }
}

if (SpeechRecognitionCtor) {
  voiceRecog = new SpeechRecognitionCtor();
  voiceRecog.lang = 'zh-CN';
  voiceRecog.interimResults = true;
  voiceRecog.continuous = false;
  voiceRecog.maxAlternatives = 1;

  voiceRecog.onresult = function (event) {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const item = event.results[i];
      if (item.isFinal) voiceFinalText += item[0].transcript;
      else interim += item[0].transcript;
    }
    const combined = (voiceFinalText + interim).trim();
    if (!combined) return;
    voiceText.value = combined;
    voiceHasResult = true;
    setVoiceStatus(interim ? '正在识别…' : '识别完成，确认无误后点 ✓ 填入');
  };

  voiceRecog.onerror = function (event) {
    const reasons = {
      'not-allowed': '麦克风权限被拒绝，请在浏览器设置里允许使用麦克风',
      'service-not-allowed': '当前浏览器无法使用语音服务，可改用服务器识别或手动输入',
      'no-speech': '没有听到声音，请靠近麦克风再试一次',
      'network': '浏览器语音服务网络不通（国内安卓 Chrome 常见），可换 iPhone Safari 使用，或配置服务器语音识别',
      'audio-capture': '没有检测到麦克风，请检查设备'
    };
    voiceErrorShown = true;
    // 浏览器识别在国内基本不可用：只要服务器识别已配置，任何失败都自动切过去
    if (asrStatusCache && event.error !== 'not-allowed' && event.error !== 'audio-capture') {
      setVoiceStatus('浏览器识别不可用，改用服务器识别…');
      startServerVoice();
      return;
    }
    const message = reasons[event.error] || ('语音识别失败（' + event.error + '），可直接在框里手写');
    setVoiceStatus(message);
    showToast(message);
  };

  voiceRecog.onend = function () {
    setVoiceRecording(false);
    if (!voicePanelOpen || recorder) return;
    if (voiceHasResult) {
      setVoiceStatus('识别完成，确认无误后点 ✓ 填入');
    } else if (!voiceErrorShown) {
      setVoiceStatus('没有听到内容，可点左下角麦克风重试');
    }
  };
}

voiceFab.addEventListener('click', async function () {
  const wantsAutoSend = pendingVoiceAutoSend;
  pendingVoiceAutoSend = false;
  if (!window.isSecureContext) {
    showToast('语音输入需要 HTTPS 访问；当前是普通 HTTP，请手动输入或让管理员开启 HTTPS');
    return;
  }
  if (recorder) return;        // 录音中由面板的 ✓ 结束
  if (voiceBusy) return;

  if (voicePanelOpen) cancelVoice();

  voiceTarget = (lastEditable && document.contains(lastEditable)) ? lastEditable : null;
  if (!voiceTarget) {
    showToast('请先点一下要填写的输入框，再点语音输入');
    return;
  }
  voiceAutoSend = wantsAutoSend;

  openVoicePanel('正在准备麦克风…');
  const useServer = await fetchAsrStatus();

  // iOS 的浏览器识别能实时出字，优先用；安卓（尤其国内）浏览器识别基本不可用，
  // 只要服务器识别已配置就直接走服务器（阿里云），保证一定能识别
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (useServer && !isIOS) {
    await startServerVoice();
    return;
  }
  if (SpeechRecognitionCtor) {
    startBrowserRecognition();
    return;
  }
  if (useServer) {
    await startServerVoice();
    return;
  }
  closeVoicePanel();
  showToast('当前浏览器不支持语音输入，请使用 Edge 或 Chrome，也可以直接打字');
  resetVoiceButton();
});

// 生成一条聊天气泡
function makeBubble(text, who) {
  const bubble = document.createElement('div');
  bubble.className = 'msg ' + who;
  bubble.textContent = text;
  return bubble;
}

// 简单的关键词规则库（离线演示，不依赖网络接口）
const chatRules = [
  {
    keys: ['怎么用', '怎么使用', '使用教程', '教程', '怎么操作', '不会用'],
    reply: '使用说明：\n1）左侧导航依次是健康数据、饮食、运动、家人健康、健康小管家、科普资讯。\n2）健康数据：点顶部评分或数据卡片，录入血压、血糖、体重，系统会自动算 BMI 和正常范围。\n3）饮食：在早餐/午餐/晚餐输入框写食物名并回车，查不到的食物由 AI 估算热量。\n4）运动：先设目标，再点运动类型开始计时，结束后自动统计。\n5）科普资讯：可搜索、点热门标签、点「刷新」看最新新闻。\n6）语音输入：先点要填的输入框，再点左下角「语音输入」说话。\n7）小管家还能直接执行指令，例如「我要开始跑步，帮我记录一下」。'
  },
  {
    keys: ['饮食', '吃', '营养', '食谱', '三餐', '热量', '早餐', '午餐', '晚餐'],
    reply: '饮食建议：三餐尽量规律，主食粗细搭配，保证每餐有一掌心大小的优质蛋白（鸡蛋、鱼、瘦肉或豆制品），再搭配两拳蔬菜。今日蛋白质目标 60g，别忘记补充哦。'
  },
  {
    keys: ['运动', '锻炼', '跑步', '健身', '步数', '拉伸', '久坐'],
    reply: '运动建议：成年人每周建议 150 分钟中等强度运动。久坐时每小时起身活动 3—5 分钟，做几组肩颈拉伸；今天目标完成率 65%，再走 2000 步就差不多达标啦。'
  },
  {
    keys: ['睡眠', '失眠', '熬夜', '睡不够', '入睡'],
    reply: '睡眠建议：尽量固定作息，睡前一小时减少看手机；卧室温度保持在 18—22℃，并保持安静昏暗。若长期入睡困难，建议记录睡眠日志并咨询医生。'
  },
  {
    keys: ['生理期', '月经', '痛经', '经期', '排卵'],
    reply: '生理期护理：注意腹部保暖，避免剧烈运动和生冷饮食；可以适量饮用温水或红糖姜茶。若疼痛明显或周期长期紊乱，建议到医院妇科检查。'
  },
  {
    keys: ['血压', '血糖', '体检', 'bmi', '体脂', '指标'],
    reply: '你的核心体征目前为：BMI 22.0（正常）、血压 110/70 mmHg、空腹血糖 5.2 mmol/L。整体处于健康范围，建议每 3—6 个月复测一次并保持规律运动。'
  },
  {
    keys: ['减肥', '减脂', '体重', '瘦'],
    reply: '减脂建议以“热量缺口 + 力量训练”为主：每天减少 300—500 kcal 摄入，每周 2—3 次力量训练，配合快走或慢跑。不要过度节食，保证蛋白质摄入才能减少肌肉流失。'
  },
  {
    keys: ['心情', '情绪', '压力', '焦虑', '难过'],
    reply: '情绪照顾同样重要：可以试试 4-7-8 呼吸法（吸气 4 秒、屏息 7 秒、呼气 8 秒），或把此刻的感受写进“心理情绪记录”。如果低落持续两周以上，建议寻求专业心理支持。'
  }
];

// 根据用户输入匹配回复
function getReply(text) {
  const lower = text.toLowerCase();
  for (let i = 0; i < chatRules.length; i++) {
    const rule = chatRules[i];
    for (let j = 0; j < rule.keys.length; j++) {
      if (lower.indexOf(rule.keys[j]) !== -1) return rule.reply;
    }
  }
  return '收到～我是健康小管家。你可以问我饮食搭配、运动计划、睡眠改善或生理期护理等问题，我会给出简单可执行的建议。';
}

// 聊天记录：悬浮窗与整页共用同一份，连后端时由服务端保存
function renderChatLog() {
  [chatBody, assistantLog].forEach(function (box) {
    if (!box) return;
    box.innerHTML = '';
    if (!chatMessages.length) {
      box.appendChild(makeBubble(CHAT_GREETING, 'bot'));
      return;
    }
    chatMessages.forEach(function (item) {
      box.appendChild(makeBubble(item.content, item.role === 'user' ? 'user' : 'bot'));
    });
    box.scrollTop = box.scrollHeight;
  });
}

// 新增一条消息并重绘两边
function pushMessage(role, content) {
  chatMessages.push({ role: role, content: content });
  if (chatMessages.length > 100) chatMessages = chatMessages.slice(-100);
  renderChatLog();
}

// 两边的“正在输入”提示，返回清除函数
function startTyping() {
  const nodes = [];
  [chatBody, assistantLog].forEach(function (box) {
    if (!box) return;
    const el = makeBubble('正在输入...', 'bot typing');
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    nodes.push(el);
  });
  return function () {
    nodes.forEach(function (el) { el.remove(); });
  };
}

// ---------- 历史对话 ----------
function formatChatTime(value) {
  if (!value) return '';
  const text = String(value).replace('T', ' ').replace(/\.\d+/, '');
  return text.slice(0, 16);
}

function renderHistoryList(items) {
  if (!assistantHistList) return;
  assistantHistList.innerHTML = '';
  assistantHistEmpty.hidden = items.length > 0;

  items.forEach(function (item) {
    const row = document.createElement('div');
    row.className = 'assistant-hist-item' + (item.id === currentConversationId ? ' active' : '');
    row.setAttribute('role', 'button');
    row.tabIndex = 0;

    const main = document.createElement('div');
    main.className = 'assistant-hist-main';
    const title = document.createElement('div');
    title.className = 'assistant-hist-title';
    title.textContent = item.title || '新对话';
    const time = document.createElement('div');
    time.className = 'assistant-hist-time';
    time.textContent = formatChatTime(item.updatedAt || item.updated_at) +
      (typeof item.count === 'number' ? ' · ' + Math.ceil(item.count / 2) + ' 轮' : '');
    main.appendChild(title);
    main.appendChild(time);

    const del = document.createElement('button');
    del.className = 'assistant-hist-del';
    del.type = 'button';
    del.title = '删除这条对话';
    del.innerHTML = '<svg class="icon"><use href="#i-close"/></svg>';

    row.addEventListener('click', function () { openConversation(item.id); });
    row.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') openConversation(item.id);
    });
    del.addEventListener('click', function (event) {
      event.stopPropagation();
      removeConversation(item.id);
    });

    row.appendChild(main);
    row.appendChild(del);
    assistantHistList.appendChild(row);
  });
}

async function loadConversationList() {
  if (!assistantHistList) return;

  if (!serverMode || !currentUser) {
    renderHistoryList(staticSessions().map(function (item) {
      return { id: item.id, title: item.title, updatedAt: item.updatedAt,
               count: item.messages.length };
    }));
    return;
  }

  try {
    const result = await api('/api/ai/conversations');
    if (result.ok && result.data.conversations) {
      renderHistoryList(result.data.conversations);
    }
  } catch (error) {
    // 拉取失败时保留当前列表
  }
}

async function openConversation(id) {
  if (!id) return;

  if (!serverMode || !currentUser) {
    const session = staticSessions().find(function (item) { return item.id === id; });
    if (!session) return;
    currentConversationId = session.id;
    chatMessages = (session.messages || []).slice();
    renderChatLog();
    loadConversationList();
    return;
  }

  try {
    const result = await api('/api/ai/conversations/' + encodeURIComponent(id));
    if (!result.ok) {
      showToast('这条对话已不存在');
      loadConversationList();
      return;
    }
    currentConversationId = result.data.id;
    chatMessages = result.data.messages || [];
    renderChatLog();
    loadConversationList();
  } catch (error) {
    showToast('网络异常，请稍后再试');
  }
}

async function removeConversation(id) {
  if (!window.confirm('删除这条对话记录？')) return;

  if (!serverMode || !currentUser) {
    const rest = staticSessions().filter(function (item) { return item.id !== id; });
    saveData(STATIC_SESSIONS_KEY, rest);
  } else {
    try {
      const result = await api('/api/ai/conversations/' + encodeURIComponent(id),
                                { method: 'DELETE' });
      if (!result.ok && result.status !== 404) {
        showToast('删除失败，请稍后再试');
        return;
      }
    } catch (error) {
      showToast('删除失败，请稍后再试');
      return;
    }
  }

  if (id === currentConversationId) {
    currentConversationId = null;
    chatMessages = [];
    renderChatLog();
  }
  loadConversationList();
  showToast('已删除');
}

// 静态演示：本机保存的多条对话
const STATIC_SESSIONS_KEY = 'chatSessions';

function staticSessions() {
  const list = loadData(STATIC_SESSIONS_KEY, []) || [];
  if (list.length) return list;
  // 兼容旧版只有一条 chatLog 的数据
  const legacy = loadData('chatLog', []) || [];
  if (!legacy.length) return [];
  const session = {
    id: 's' + Date.now(),
    title: (legacy[0].content || '').slice(0, 24),
    updatedAt: new Date().toISOString(),
    messages: legacy
  };
  saveData(STATIC_SESSIONS_KEY, [session]);
  return [session];
}

function staticSaveCurrent() {
  if (!chatMessages.length) return;
  const list = staticSessions().slice();
  let index = -1;
  for (let i = 0; i < list.length; i++) {
    if (list[i].id === currentConversationId) { index = i; break; }
  }
  if (index === -1) {
    currentConversationId = 's' + Date.now();
    list.unshift({
      id: currentConversationId,
      title: (chatMessages[0].content || '').slice(0, 24),
      updatedAt: new Date().toISOString(),
      messages: chatMessages.slice()
    });
  } else {
    const item = list.splice(index, 1)[0];
    item.messages = chatMessages.slice();
    item.updatedAt = new Date().toISOString();
    list.unshift(item);
  }
  saveData(STATIC_SESSIONS_KEY, list.slice(0, 50));
}

async function loadChatHistory() {
  if (!serverMode || !currentUser) {
    // 静态演示：读取本机最近一条对话
    const list = staticSessions();
    if (list.length) {
      currentConversationId = list[0].id;
      chatMessages = (list[0].messages || []).slice();
    } else {
      chatMessages = [];
    }
    renderChatLog();
    return;
  }

  let result = null;
  try {
    result = await api('/api/ai/history?limit=100');
  } catch (error) {
    return;
  }
  if (!result || !result.ok) return;

  currentConversationId = result.data.conversationId || null;
  chatMessages = result.data.messages || [];
  renderChatLog();
}

// 执行 AI 返回的动作：开始运动计时 / 写入某一餐
function runAiAction(action) {
  if (!action || !action.type) return;

  if (action.type === 'sport_start') {
    const name = action.sport || '跑步';
    startSportSession(name);
    switchPage('sport');
    showToast('已开始记录「' + name + '」，结束后会自动统计时长和热量');
    return;
  }

  if (action.type === 'meal_add') {
    const meal = action.meal || '加餐';
    if (!action.foods || !action.foods.length) {
      showToast('已识别到饮食内容，但没有估算出热量，请到「饮食」页手动确认');
      return;
    }
    const totals = action.total || action.foods.reduce(function (sum, food) {
      return {
        kcal: sum.kcal + (Number(food.kcal) || 0),
        protein: sum.protein + (Number(food.protein) || 0),
        carb: sum.carb + (Number(food.carb) || 0),
        fat: sum.fat + (Number(food.fat) || 0),
        fiber: sum.fiber + (Number(food.fiber) || 0)
      };
    }, { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 });

    saveMealRecord(meal, action.text || 'AI 记录', totals);
    renderMealLog();
    switchPage('diet');
    showToast('已记入' + meal + '：约 ' + Math.round(totals.kcal) + ' kcal');
  }
}

// 发送消息：悬浮窗和整页共用；传入文本表示来自整页输入框
function sendChat(rawText) {
  const fromAssistant = typeof rawText === 'string';
  const text = (fromAssistant ? rawText : chatInput.value).trim();
  if (!text) return;

  if (fromAssistant) assistantInput.value = '';
  else chatInput.value = '';

  pushMessage('user', text);
  const stopTyping = startTyping();

  // 纯静态演示：本地规则回复，并把对话留在本机
  if (!serverMode || !currentUser) {
    const reply = getReply(text);

    setTimeout(function () {
      stopTyping();
      pushMessage('assistant', reply);
      staticSaveCurrent();
      if (!assistantHistPanel.hidden) loadConversationList();
    }, 500);
    return;
  }

  // 连后端：消息与回复都由服务端保存
  api('/api/ai/chat', {
    method: 'POST',
    body: { message: text, conversationId: currentConversationId }
  })
    .then(function (result) {
      stopTyping();
      if (result.ok && result.data.reply) {
        if (result.data.conversationId) currentConversationId = result.data.conversationId;
        pushMessage('assistant', result.data.reply);
        runAiAction(result.data.action);
        if (!assistantHistPanel.hidden) loadConversationList();
        if (result.data.degraded) {
          showToast(result.data.configured
            ? 'AI 服务暂时不可用，已返回兜底建议'
            : '尚未配置 AI 密钥，当前为兜底回复');
        }
      } else {
        pushMessage('assistant', '抱歉，暂时无法获取回复，请稍后再试。');
      }
    })
    .catch(function () {
      stopTyping();
      pushMessage('assistant', '网络异常，请稍后再试。');
    });
}

document.getElementById('chatSend').addEventListener('click', function () {
  sendChat();
});

// 回车发送（悬浮窗）
chatInput.addEventListener('keydown', function (event) {
  if (event.key === 'Enter') sendChat();
});

// 整页聊天：发送、回车、开启新对话
document.getElementById('assistantSend').addEventListener('click', function () {
  sendChat(assistantInput.value);
});

// 快捷提问：这个网页怎么用 / 怎么语音输入 / 示例指令
const assistantQuick = document.getElementById('assistantQuick');
if (assistantQuick) {
  assistantQuick.addEventListener('click', function (event) {
    const button = event.target.closest('button[data-question]');
    if (!button) return;
    sendChat(button.dataset.question);
  });
}

assistantInput.addEventListener('keydown', function (event) {
  if (event.key === 'Enter') sendChat(assistantInput.value);
});

// 开启新对话：不删除旧记录，旧对话保存在「历史对话」里
document.getElementById('assistantNew').addEventListener('click', function () {
  chatMessages = [];
  currentConversationId = null;
  renderChatLog();
  if (!assistantHistPanel.hidden) loadConversationList();
  assistantInput.focus();
  showToast('已开启新对话，旧对话可在「历史对话」里找回');
});

// 历史对话：展开 / 收起
assistantHistoryBtn.addEventListener('click', function () {
  const willOpen = assistantHistPanel.hidden;
  assistantHistPanel.hidden = !willOpen;
  if (willOpen) loadConversationList();
});

// 首次进入时先把问候语画到两边
renderChatLog();

/* ==========================================================
   八、键盘 Esc：关闭弹窗与聊天窗
   ========================================================== */
document.addEventListener('keydown', function (event) {
  if (event.key !== 'Escape') return;
  closeCrop();
  closeProfile();
  closeChat();
  closeMask(periodMask);
  closeMask(familyMask);
  closeMask(memberMask);
  closeMask(reminderMask);
  closeMask(sportMask);
  closeMask(sportDataMask);
  closeMask(vitalMask);
  closeMask(foodMask);
  closeMask(scoreMask);
  closeMask(memberRecordsMask);
  closeMask(newsMask);
  closeTagMenus();
});