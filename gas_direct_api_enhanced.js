/**
 * 既存のGASコードを拡張して、直接Web App API化
 * AIcastアプリから直接HTTP POSTで呼び出し可能
 */

// 既存の設定をそのまま使用
const CLIENT_ID = 'a21EX2p6ZjU0R21SR0NHLU9PX0I6MTpjaQ'
const CLIENT_SECRET = 'GBJdzTUfsugbqiR42o8shVfbzzClbggTwTFQ-W0o1LOfYZmBZT'
const SHEET_NAME = '投稿メッセージリスト'
const RETWEET_SHEET_NAME = 'リツイート予約リスト'
const MY_USER_ID = PropertiesService.getScriptProperties().getProperty('MY_USER_ID');

/**
 * ★★★ 新機能：Web App API エンドポイント ★★★
 * AIcastアプリから直接HTTP POSTで呼び出される
 * スプレッドシートを介さない直接実行
 */
function doPost(e) {
  try {
    // CORS対応
    const response = ContentService.createTextOutput();
    response.setMimeType(ContentService.MimeType.JSON);
    
    // リクエストボディを解析
    const requestData = JSON.parse(e.postData.contents);
    const action = requestData.action;
    
    console.log('受信リクエスト:', JSON.stringify(requestData));
    
    // 認証チェック
    const service = getService();
    if (!service.hasAccess()) {
      return response.setContent(JSON.stringify({
        status: 'error',
        message: '認証が必要です。GAS側でmain()関数を実行して認証を完了してください。'
      }));
    }
    
    let result;
    switch (action) {
      case 'post':
        result = directPostTweet(service, requestData.text, requestData.cast_name);
        break;
      case 'retweet':
        result = directRetweet(service, requestData.tweet_id, requestData.cast_name);
        break;
      case 'quote_tweet':
        result = directQuoteTweet(service, requestData.tweet_id, requestData.comment, requestData.cast_name);
        break;
      case 'schedule_retweet':
        result = directScheduleRetweet(service, requestData.tweet_id, requestData.comment, requestData.scheduled_at, requestData.cast_name);
        break;
      default:
        throw new Error(`未対応のアクション: ${action}`);
    }
    
    return response.setContent(JSON.stringify({
      status: 'success',
      data: result,
      message: '処理が完了しました',
      timestamp: new Date().toISOString()
    }));
    
  } catch (error) {
    console.error('API実行エラー:', error);
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: error.toString(),
      timestamp: new Date().toISOString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * GET リクエスト対応（ヘルスチェック等）
 */
function doGet(e) {
  const service = getService();
  return ContentService.createTextOutput(JSON.stringify({
    status: 'active',
    service: 'AIcast GAS Direct API',
    authenticated: service.hasAccess(),
    timestamp: new Date().toISOString(),
    available_actions: ['post', 'retweet', 'quote_tweet', 'schedule_retweet']
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * 直接ツイート投稿（スプレッドシート不要）
 */
function directPostTweet(service, text, castName) {
  if (!text || text.trim() === '') {
    throw new Error('ツイート内容が空です');
  }
  
  const url = 'https://api.twitter.com/2/tweets';
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    muteHttpExceptions: true,
    payload: JSON.stringify({ text: text })
  });
  
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();
  const result = JSON.parse(responseBody);
  
  if (responseCode < 200 || responseCode >= 300) {
    throw new Error(`ツイート投稿失敗 ${responseCode}: ${responseBody}`);
  }
  
  // 成功ログをスプレッドシートに記録（オプション）
  logToSpreadsheet('post', {
    tweet_id: result.data.id,
    text: text,
    cast_name: castName,
    executed_at: new Date(),
    status: 'success'
  });
  
  return {
    tweet_id: result.data.id,
    text: result.data.text,
    cast_name: castName
  };
}

/**
 * 直接リツイート（スプレッドシート不要）
 */
function directRetweet(service, tweetId, castName) {
  if (!tweetId) {
    throw new Error('ツイートIDが必要です');
  }
  
  const url = `https://api.twitter.com/2/users/${MY_USER_ID}/retweets`;
  const payload = { 'tweet_id': tweetId.toString() };
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();
  
  if (responseCode < 200 || responseCode >= 300) {
    throw new Error(`リツイート失敗 ${responseCode}: ${responseBody}`);
  }
  
  const result = JSON.parse(responseBody);
  
  // 成功ログをスプレッドシートに記録（オプション）
  logToSpreadsheet('retweet', {
    original_tweet_id: tweetId,
    retweeted: result.data.retweeted,
    cast_name: castName,
    executed_at: new Date(),
    status: 'success'
  });
  
  return {
    retweeted: result.data.retweeted,
    original_tweet_id: tweetId,
    cast_name: castName
  };
}

/**
 * 直接引用ツイート（スプレッドシート不要）
 */
function directQuoteTweet(service, tweetId, comment, castName) {
  if (!tweetId || !comment) {
    throw new Error('ツイートIDとコメントが必要です');
  }
  
  const url = 'https://api.twitter.com/2/tweets';
  const payload = {
    'text': comment.toString(),
    'quote_tweet_id': tweetId.toString()
  };
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();
  const result = JSON.parse(responseBody);
  
  if (responseCode < 200 || responseCode >= 300) {
    throw new Error(`引用ツイート失敗 ${responseCode}: ${responseBody}`);
  }
  
  // 成功ログをスプレッドシートに記録（オプション）
  logToSpreadsheet('quote_tweet', {
    tweet_id: result.data.id,
    original_tweet_id: tweetId,
    comment: comment,
    cast_name: castName,
    executed_at: new Date(),
    status: 'success'
  });
  
  return {
    tweet_id: result.data.id,
    text: result.data.text,
    original_tweet_id: tweetId,
    cast_name: castName
  };
}

/**
 * 直接予約リツイート（GASトリガー使用）
 */
function directScheduleRetweet(service, tweetId, comment, scheduledAt, castName) {
  try {
    const scheduledDate = new Date(scheduledAt);
    
    // 未来の日時かチェック
    if (scheduledDate <= new Date()) {
      throw new Error('予約時刻は未来の時刻を指定してください');
    }
    
    // 実行用トリガーを作成
    const trigger = ScriptApp.newTrigger('executeDirectScheduledRetweet')
      .timeBased()
      .at(scheduledDate)
      .create();
    
    // トリガー情報をPropertiesServiceに保存
    const triggerData = {
      tweet_id: tweetId.toString(),
      comment: comment ? comment.toString() : '',
      cast_name: castName,
      trigger_id: trigger.getUniqueId(),
      scheduled_at: scheduledAt,
      created_at: new Date().toISOString()
    };
    
    const properties = PropertiesService.getScriptProperties();
    properties.setProperty(`direct_trigger_${trigger.getUniqueId()}`, JSON.stringify(triggerData));
    
    // 予約ログをスプレッドシートに記録（オプション）
    logToSpreadsheet('schedule_retweet', {
      tweet_id: tweetId,
      comment: comment,
      scheduled_at: scheduledDate,
      cast_name: castName,
      trigger_id: trigger.getUniqueId(),
      status: 'scheduled'
    });
    
    return {
      trigger_id: trigger.getUniqueId(),
      tweet_id: tweetId,
      comment: comment,
      scheduled_at: scheduledAt,
      cast_name: castName,
      message: 'リツイートが予約されました'
    };
    
  } catch (error) {
    throw new Error(`予約設定失敗: ${error.message}`);
  }
}

/**
 * 予約実行用関数（トリガーから呼ばれる）
 */
function executeDirectScheduledRetweet(e) {
  try {
    const triggerId = e.triggerUid;
    const properties = PropertiesService.getScriptProperties();
    const triggerDataStr = properties.getProperty(`direct_trigger_${triggerId}`);
    
    if (!triggerDataStr) {
      console.error('トリガーデータが見つかりません:', triggerId);
      return;
    }
    
    const triggerData = JSON.parse(triggerDataStr);
    const service = getService();
    
    if (!service.hasAccess()) {
      console.error('認証が無効です');
      return;
    }
    
    // リツイート実行
    let result;
    if (triggerData.comment && triggerData.comment.trim() !== '') {
      result = directQuoteTweet(service, triggerData.tweet_id, triggerData.comment, triggerData.cast_name);
    } else {
      result = directRetweet(service, triggerData.tweet_id, triggerData.cast_name);
    }
    
    console.log('予約リツイート実行完了:', result);
    
    // 実行完了ログ
    logToSpreadsheet('executed_schedule', {
      ...triggerData,
      executed_at: new Date(),
      result: result,
      status: 'completed'
    });
    
    // クリーンアップ
    properties.deleteProperty(`direct_trigger_${triggerId}`);
    
    // トリガー削除
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getUniqueId() === triggerId) {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
  } catch (error) {
    console.error('予約リツイート実行エラー:', error);
    
    // エラーログ
    const triggerId = e.triggerUid;
    logToSpreadsheet('execute_error', {
      trigger_id: triggerId,
      error: error.toString(),
      executed_at: new Date(),
      status: 'error'
    });
  }
}

/**
 * ログ記録用関数（スプレッドシートに記録）
 */
function logToSpreadsheet(action, data) {
  try {
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    let logSheet;
    
    try {
      logSheet = spreadsheet.getSheetByName('API実行ログ');
    } catch (e) {
      // ログシートが存在しない場合は作成
      logSheet = spreadsheet.insertSheet('API実行ログ');
      logSheet.getRange(1, 1, 1, 8).setValues([
        ['実行日時', 'アクション', 'キャスト名', 'ツイートID', 'コメント', 'ステータス', 'トリガーID', '詳細']
      ]);
    }
    
    const logRow = [
      new Date(),
      action,
      data.cast_name || '',
      data.tweet_id || data.original_tweet_id || '',
      data.comment || '',
      data.status || '',
      data.trigger_id || '',
      JSON.stringify(data)
    ];
    
    logSheet.appendRow(logRow);
    
  } catch (e) {
    console.error('ログ記録エラー:', e);
  }
}

// ★★★ 以下は既存のコードをそのまま保持 ★★★

function getService() {
  pkceChallengeVerifier();
  const userProps = PropertiesService.getUserProperties();
  const scriptProps = PropertiesService.getScriptProperties();
  
  return OAuth2.createService('twitter')
    .setAuthorizationBaseUrl('https://twitter.com/i/oauth2/authorize')
    .setTokenUrl('https://api.twitter.com/2/oauth2/token?code_verifier=' + userProps.getProperty("code_verifier"))
    .setClientId(CLIENT_ID)
    .setClientSecret(CLIENT_SECRET)
    .setCallbackFunction('authCallback')
    .setPropertyStore(userProps)
    .setScope('users.read tweet.read tweet.write offline.access')
    .setParam('response_type', 'code')
    .setParam('code_challenge_method', 'S256')
    .setParam('code_challenge', userProps.getProperty("code_challenge"))
    .setTokenHeaders({
      'Authorization': 'Basic ' + Utilities.base64Encode(CLIENT_ID + ':' + CLIENT_SECRET),
      'Content-Type': 'application/x-www-form-urlencoded'
    })
}

function authCallback(request) {
  const service = getService();
  const authorized = service.handleCallback(request);
  if (authorized) {
    return HtmlService.createHtmlOutput('Success!');
  } else {
    return HtmlService.createHtmlOutput('Denied.');
  }
}

function pkceChallengeVerifier() {
  var userProps = PropertiesService.getUserProperties();
  if (!userProps.getProperty("code_verifier")) {
    var verifier = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    
    for (var i = 0; i < 128; i++) {
      verifier += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    
    var sha256Hash = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, verifier)
    var challenge = Utilities.base64Encode(sha256Hash)
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')
    userProps.setProperty("code_verifier", verifier)
    userProps.setProperty("code_challenge", challenge)
  }
}

function logRedirectUri() {
  var service = getService();
  Logger.log(service.getRedirectUri());
}

function main() {
  const service = getService();
  if (service.hasAccess()) {
    Logger.log("Already authorized");
  } else {
    const authorizationUrl = service.getAuthorizationUrl();
    Logger.log('Open the following URL and re-run the script: %s', authorizationUrl);
  }
}

// 既存のスプレッドシート経由機能も保持
function getSpreadsheetData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const range = sheet.getDataRange();
  return range.getValues();
}

function postScheduledTweets() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const rows = sheet.getDataRange().getValues();
  const now = new Date();
  
  for (let i = 1; i < rows.length; i++) {
    const [scheduledTime, tweetContent, status] = rows[i];
    if (scheduledTime && tweetContent && new Date(scheduledTime) <= now && status !== "投稿済") {
      sendTweet(tweetContent);
      sheet.getRange(i + 1, 3).setValue("投稿済");
    }
  }
}

function sendTweet(tweetContent) {
  if (!tweetContent) {
    Logger.log("No tweet content provided");
    return;
  }
  
  var service = getService();
  if (service.hasAccess()) {
    var url = 'https://api.twitter.com/2/tweets';
    var response = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + service.getAccessToken()
      },
      muteHttpExceptions: true,
      payload: JSON.stringify({ text: tweetContent })
    });
    
    var result = JSON.parse(response.getContentText());
    Logger.log(JSON.stringify(result, null, 2));
  } else {
    var authorizationUrl = service.getAuthorizationUrl();
    Logger.log('Open the following URL and re-run the script: %s', authorizationUrl);
  }
}

function retweetMain() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(RETWEET_SHEET_NAME);
  if (!sheet) {
    console.error(`シート「${RETWEET_SHEET_NAME}」が見つかりません。`);
    return;
  }
  
  const service = getService();
  if (!service.hasAccess()) {
    console.log('認証が必要です。main関数を実行して認証URLを取得してください。');
    return;
  }
  
  const data = sheet.getDataRange().getValues();
  const now = new Date();
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const executionDateTimeValue = row[0];
    const tweetId = row[1];
    const comment = row[2];
    const status = row[3];
    
    if (!executionDateTimeValue || !tweetId) continue;
    
    const executionDateTime = new Date(executionDateTimeValue);
    
    if (status !== '実行済み' && executionDateTime <= now) {
      try {
        if (comment && comment.toString().trim() !== '') {
          postQuoteTweet(service, tweetId.toString(), comment.toString());
        } else {
          postRetweet(service, tweetId.toString());
        }
        sheet.getRange(i + 1, 4).setValue('実行済み');
        sheet.getRange(i + 1, 5).setValue(new Date());
        console.log(`Success: Row ${i + 1}, Tweet ID: ${tweetId}`);
      } catch (e) {
        sheet.getRange(i + 1, 4).setValue('エラー');
        sheet.getRange(i + 1, 5).setValue(e.message);
        console.error(`Error: Row ${i + 1}, Tweet ID: ${tweetId}, Message: ${e.message}`);
      }
    }
  }
}

function postRetweet(service, tweetId) {
  const url = `https://api.twitter.com/2/users/${MY_USER_ID}/retweets`;
  const payload = { 'tweet_id': tweetId };
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();
  
  if (responseCode < 200 || responseCode >= 300) {
    throw new Error(`API Error ${responseCode}: ${responseBody}`);
  }
}

function postQuoteTweet(service, tweetId, comment) {
  const url = 'https://api.twitter.com/2/tweets';
  const payload = {
    'text': comment,
    'quote_tweet_id': tweetId
  };
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();
  
  if (responseCode < 200 || responseCode >= 300) {
    throw new Error(`API Error ${responseCode}: ${responseBody}`);
  }
}