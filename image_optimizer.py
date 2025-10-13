# 画像最適化モジュール
from PIL import Image
import io
import os

def optimize_image_for_upload(image_path, max_size=(1024, 1024), quality=85, max_file_size_mb=5):
    """
    画像を最適化してアップロード用に調整
    
    Args:
        image_path: 元画像のパス
        max_size: 最大サイズ（幅、高さ）
        quality: JPEG品質（1-100）
        max_file_size_mb: 最大ファイルサイズ（MB）
    
    Returns:
        optimized_path: 最適化された画像のパス
        success: 成功フラグ
        message: 処理メッセージ
    """
    try:
        # 画像を開く
        with Image.open(image_path) as img:
            # RGBAをRGBに変換（JPEG保存用）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 透明部分を白背景に変換
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # アスペクト比を保持してリサイズ
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 最適化されたファイル名を生成
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            optimized_path = os.path.join(
                os.path.dirname(image_path), 
                f"{base_name}_optimized.jpg"
            )
            
            # ファイルサイズが目標値以下になるまで品質を調整
            current_quality = quality
            max_file_size_bytes = max_file_size_mb * 1024 * 1024
            
            while current_quality > 10:
                # メモリ上で圧縮をテスト
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=current_quality, optimize=True)
                
                if output.tell() <= max_file_size_bytes:
                    # 目標サイズ以下なので保存
                    with open(optimized_path, 'wb') as f:
                        f.write(output.getvalue())
                    
                    file_size_mb = output.tell() / (1024 * 1024)
                    return optimized_path, True, f"画像を最適化しました（{img.size[0]}x{img.size[1]}、{file_size_mb:.1f}MB、品質{current_quality}）"
                
                # サイズが大きすぎる場合は品質を下げる
                current_quality -= 10
                output.close()
            
            # 最低品質でも大きすぎる場合はさらにサイズを縮小
            if current_quality <= 10:
                smaller_size = (max_size[0] // 2, max_size[1] // 2)
                img.thumbnail(smaller_size, Image.Resampling.LANCZOS)
                
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=60, optimize=True)
                
                with open(optimized_path, 'wb') as f:
                    f.write(output.getvalue())
                
                file_size_mb = output.tell() / (1024 * 1024)
                return optimized_path, True, f"画像を大幅圧縮しました（{img.size[0]}x{img.size[1]}、{file_size_mb:.1f}MB）"
            
    except Exception as e:
        return None, False, f"画像最適化エラー: {str(e)}"

def get_image_info(image_path):
    """画像の基本情報を取得"""
    try:
        with Image.open(image_path) as img:
            file_size = os.path.getsize(image_path)
            file_size_mb = file_size / (1024 * 1024)
            
            return {
                'size': img.size,
                'mode': img.mode,
                'format': img.format,
                'file_size_mb': round(file_size_mb, 2)
            }
    except Exception as e:
        return {'error': str(e)}

def validate_image_for_twitter(image_path):
    """Twitter投稿用の画像バリデーション"""
    try:
        info = get_image_info(image_path)
        if 'error' in info:
            return False, f"画像読み込みエラー: {info['error']}"
        
        # Twitterの画像制限をチェック
        max_size_mb = 5  # Twitter画像の最大サイズ
        max_pixels = 1024 * 1024  # 1M pixels
        
        warnings = []
        
        if info['file_size_mb'] > max_size_mb:
            warnings.append(f"ファイルサイズが大きすぎます（{info['file_size_mb']}MB > {max_size_mb}MB）")
        
        pixel_count = info['size'][0] * info['size'][1]
        if pixel_count > max_pixels:
            warnings.append(f"画素数が多すぎます（{pixel_count:,} > {max_pixels:,}）")
        
        if warnings:
            return False, "、".join(warnings)
        
        return True, f"画像OK（{info['size'][0]}x{info['size'][1]}、{info['file_size_mb']}MB）"
        
    except Exception as e:
        return False, f"バリデーションエラー: {str(e)}"