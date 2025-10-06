/**
 * スプレッドシート不要の直接GAS→X API投稿システム
 * Web Appとしてデプロイして使用
 */

/**
 * メイン関数 - Web Appエンドポイント
 * POST リクエストを受け取り、X APIに投稿
 */
function doPost(e) {
  try {
    // リクエストボディからデータを取得
    const requestData = JSON.parse(e.postData.contents);
    
    const action = requestData.action; // 'post', 'retweet', 'quote_tweet'
    const accountId = requestData.account_id;
    
    // アカウント設定を取得
    const config = getAccountConfig(accountId);
    if (!config) {
      return ContentService.createTextOutput(JSON.stringify({
        status: 'error',
        message: `アカウントID ${accountId} の設定が見つかりません`
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    let result;
    switch (action) {
      case 'post':
        result = postTweet(config, requestData.text, requestData.image_urls);
        break;
      case 'retweet':
        result = retweetPost(config, requestData.tweet_id);
        break;
      case 'quote_tweet':
        result = quoteTweet(config, requestData.tweet_id, requestData.comment);
        break;
      case 'schedule_retweet':
        result = scheduleRetweet(config, requestData.tweet_id, requestData.comment, requestData.scheduled_at);
        break;
      default:
        throw new Error(`未対応のアクション: ${action}`);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: 'success',
      data: result,
      message: '処理が完了しました'
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    console.error('エラー:', error);
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * アカウント設定を取得
 * スプレッドシートまたはPropertiesServiceから設定を読み込み
 */
function getAccountConfig(accountId) {
  // Method 1: PropertiesServiceを使用（推奨）
  const properties = PropertiesService.getScriptProperties();
  const configKey = `account_${accountId}`;
  const configStr = properties.getProperty(configKey);
  
  if (configStr) {
    return JSON.parse(configStr);
  }
  
  // Method 2: スプレッドシートから読み込み（フォールバック）
  try {
    const sheet = SpreadsheetApp.openById('YOUR_CONFIG_SPREADSHEET_ID').getSheetByName('アカウント設定');
    const data = sheet.getDataRange().getValues();
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === accountId) {
        return {
          account_id: data[i][0],
          consumer_key: data[i][1],
          consumer_secret: data[i][2],
          access_token: data[i][3],
          access_token_secret: data[i][4],
          bearer_token: data[i][5]
        };
      }
    }
  } catch (e) {
    console.error('スプレッドシート設定読み込みエラー:', e);
  }
  
  return null;
}

/**
 * 通常のツイート投稿
 */
function postTweet(config, text, imageUrls = []) {
  const service = getOAuthService(config);
  
  if (!service.hasAccess()) {
    throw new Error('X API認証が必要です');
  }
  
  // 画像アップロード（必要な場合）
  const mediaIds = [];
  if (imageUrls && imageUrls.length > 0) {
    for (const imageUrl of imageUrls.slice(0, 4)) { // 最大4枚
      const mediaId = uploadImageFromUrl(config, imageUrl);
      if (mediaId) mediaIds.push(mediaId);
    }
  }
  
  // ツイート投稿
  const url = 'https://api.twitter.com/2/tweets';
  const payload = { text: text };
  
  if (mediaIds.length > 0) {
    payload.media = { media_ids: mediaIds };
  }
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + config.bearer_token
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseData = JSON.parse(response.getContentText());
  
  if (response.getResponseCode() !== 201) {
    throw new Error(`ツイート投稿失敗: ${JSON.stringify(responseData)}`);
  }
  
  return responseData;
}

/**
 * リツイート
 */
function retweetPost(config, tweetId) {
  const url = `https://api.twitter.com/2/users/${config.user_id}/retweets`;
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + config.bearer_token
    },
    payload: JSON.stringify({
      tweet_id: tweetId
    }),
    muteHttpExceptions: true
  });
  
  const responseData = JSON.parse(response.getContentText());
  
  if (response.getResponseCode() !== 200) {
    throw new Error(`リツイート失敗: ${JSON.stringify(responseData)}`);
  }
  
  return responseData;
}

/**
 * 引用ツイート
 */
function quoteTweet(config, tweetId, comment) {
  const url = 'https://api.twitter.com/2/tweets';
  
  const payload = {
    text: comment,
    quote_tweet_id: tweetId
  };
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + config.bearer_token
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseData = JSON.parse(response.getContentText());
  
  if (response.getResponseCode() !== 201) {
    throw new Error(`引用ツイート失敗: ${JSON.stringify(responseData)}`);
  }
  
  return responseData;
}

/**
 * 予約リツイート（GASトリガー使用）
 */
function scheduleRetweet(config, tweetId, comment, scheduledAt) {
  // 実行予定時刻のトリガーを作成
  const scheduledDate = new Date(scheduledAt);
  const trigger = ScriptApp.newTrigger('executeScheduledRetweet')
    .timeBased()
    .at(scheduledDate)
    .create();
  
  // 実行データを保存
  const properties = PropertiesService.getScriptProperties();
  const triggerData = {
    account_id: config.account_id,
    tweet_id: tweetId,
    comment: comment,
    trigger_id: trigger.getUniqueId()
  };
  
  properties.setProperty(`trigger_${trigger.getUniqueId()}`, JSON.stringify(triggerData));
  
  return {
    trigger_id: trigger.getUniqueId(),
    scheduled_at: scheduledAt,
    message: 'リツイートが予約されました'
  };
}

/**
 * 予約実行用関数（トリガーから呼ばれる）
 */
function executeScheduledRetweet(e) {
  try {
    const triggerId = e.triggerUid;
    const properties = PropertiesService.getScriptProperties();
    const triggerDataStr = properties.getProperty(`trigger_${triggerId}`);
    
    if (!triggerDataStr) {
      console.error('トリガーデータが見つかりません:', triggerId);
      return;
    }
    
    const triggerData = JSON.parse(triggerDataStr);
    const config = getAccountConfig(triggerData.account_id);
    
    if (!config) {
      console.error('アカウント設定が見つかりません:', triggerData.account_id);
      return;
    }
    
    // リツイート実行
    let result;
    if (triggerData.comment && triggerData.comment.trim()) {
      result = quoteTweet(config, triggerData.tweet_id, triggerData.comment);
    } else {
      result = retweetPost(config, triggerData.tweet_id);
    }
    
    console.log('予約リツイート実行完了:', result);
    
    // 実行済みデータのクリーンアップ
    properties.deleteProperty(`trigger_${triggerId}`);
    
    // トリガーを削除
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getUniqueId() === triggerId) {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
  } catch (error) {
    console.error('予約リツイート実行エラー:', error);
  }
}

/**
 * OAuth 1.0a サービス取得（必要に応じて）
 */
function getOAuthService(config) {
  // OAuth 1.0a が必要な場合の実装
  // Bearer Tokenで十分な場合は不要
  return {
    hasAccess: () => true,
    getAccessToken: () => config.bearer_token
  };
}

/**
 * 画像アップロード（URL から）
 */
function uploadImageFromUrl(config, imageUrl) {
  try {
    const imageBlob = UrlFetchApp.fetch(imageUrl).getBlob();
    
    const response = UrlFetchApp.fetch('https://upload.twitter.com/1.1/media/upload.json', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + config.bearer_token
      },
      payload: {
        media: imageBlob
      },
      muteHttpExceptions: true
    });
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200) {
      return responseData.media_id_string;
    } else {
      console.error('画像アップロードエラー:', responseData);
      return null;
    }
  } catch (e) {
    console.error('画像処理エラー:', e);
    return null;
  }
}