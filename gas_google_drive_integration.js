/**
 * Google Drive対応 X API画像投稿 GASコード例
 */

/**
 * Google Drive画像付きツイートを投稿する
 * @param {string} text - 投稿テキスト
 * @param {Array} driveUrls - Google Drive画像URLの配列（最大4個）
 */
function postTweetWithDriveImages(text, driveUrls) {
  const service = getService();
  
  if (!service.hasAccess()) {
    throw new Error('認証が必要です');
  }
  
  // Google Drive画像をダウンロードしてアップロード
  const mediaIds = [];
  
  for (let i = 0; i < Math.min(driveUrls.length, 4); i++) {
    if (driveUrls[i] && driveUrls[i].trim()) {
      try {
        const mediaId = uploadImageFromDriveUrl(driveUrls[i]);
        if (mediaId) {
          mediaIds.push(mediaId);
        }
      } catch (e) {
        console.error(`Google Drive画像 ${i+1} のアップロードに失敗:`, e);
      }
    }
  }
  
  // ツイート投稿
  const url = 'https://api.twitter.com/2/tweets';
  const payload = {
    text: text
  };
  
  if (mediaIds.length > 0) {
    payload.media = { media_ids: mediaIds };
  }
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken()
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  return JSON.parse(response.getContentText());
}

/**
 * Google Drive URLから画像をダウンロードしてX APIにアップロード
 * @param {string} driveUrl - Google Drive画像URL
 * @returns {string} - メディアID
 */
function uploadImageFromDriveUrl(driveUrl) {
  try {
    // Google Drive URLをファイルIDに変換
    const fileId = extractFileIdFromDriveUrl(driveUrl);
    if (!fileId) {
      throw new Error('無効なGoogle Drive URL: ' + driveUrl);
    }
    
    // Google Drive APIでファイルを取得
    const driveFile = DriveApp.getFileById(fileId);
    const imageBlob = driveFile.getBlob();
    
    // ファイルサイズチェック（5MB制限）
    if (imageBlob.getBytes().length > 5 * 1024 * 1024) {
      throw new Error('ファイルサイズが5MBを超えています');
    }
    
    // ファイル形式チェック
    const contentType = imageBlob.getContentType();
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(contentType)) {
      throw new Error('対応していないファイル形式: ' + contentType);
    }
    
    // X API v1.1のメディアアップロードエンドポイントを使用
    const uploadUrl = 'https://upload.twitter.com/1.1/media/upload.json';
    
    const uploadResponse = UrlFetchApp.fetch(uploadUrl, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + service.getAccessToken()
      },
      payload: {
        media: imageBlob
      },
      muteHttpExceptions: true
    });
    
    const result = JSON.parse(uploadResponse.getContentText());
    
    if (result.media_id_string) {
      console.log(`Google Drive画像アップロード成功: ${fileId} -> ${result.media_id_string}`);
      return result.media_id_string;
    } else {
      throw new Error('メディアアップロードに失敗: ' + JSON.stringify(result));
    }
    
  } catch (e) {
    console.error('Google Drive画像アップロードエラー:', e);
    return null;
  }
}

/**
 * Google Drive URLからファイルIDを抽出
 * @param {string} driveUrl - Google Drive URL
 * @returns {string} - ファイルID
 */
function extractFileIdFromDriveUrl(driveUrl) {
  if (!driveUrl) return null;
  
  // パターン1: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
  let match = driveUrl.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  
  // パターン2: https://drive.google.com/open?id=FILE_ID
  match = driveUrl.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  
  // パターン3: https://drive.google.com/uc?export=view&id=FILE_ID
  match = driveUrl.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  
  return null;
}

/**
 * メイン関数を更新（Google Drive対応）
 */
function postScheduledTweetsWithDriveImages() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const rows = sheet.getDataRange().getValues();
  
  const now = new Date();
  
  // ヘッダー行をスキップして処理
  for (let i = 1; i < rows.length; i++) {
    const [scheduledTime, tweetContent, castName, imageUrl1, imageUrl2, imageUrl3, imageUrl4, status] = rows[i];
    
    // スケジュールされた時間が現在時刻以前で、まだ投稿されていない場合
    if (scheduledTime && tweetContent && new Date(scheduledTime) <= now && status !== "投稿済") {
      
      // 画像URLを配列にまとめる
      const imageUrls = [imageUrl1, imageUrl2, imageUrl3, imageUrl4].filter(url => url && url.trim());
      
      try {
        if (imageUrls.length > 0) {
          // Google Drive画像付きツイート
          const result = postTweetWithDriveImages(tweetContent, imageUrls);
          console.log('Google Drive画像付きツイート投稿成功:', result);
        } else {
          // 通常のツイート
          sendTweet(tweetContent);
        }
        
        // ステータスを「投稿済み」に更新
        sheet.getRange(i + 1, 8).setValue("投稿済"); // status列
        
      } catch (error) {
        console.error(`行 ${i + 1} の投稿に失敗:`, error);
        sheet.getRange(i + 1, 8).setValue("エラー: " + error.message);
      }
    }
  }
}

/**
 * Google Drive APIを有効化する必要があります
 * Google Apps Script エディタで以下を実行：
 * 1. 「リソース」→「Googleの高度なサービス」
 * 2. 「Drive API」を有効化
 * 3. Google Cloud Console でも Drive API を有効化
 */