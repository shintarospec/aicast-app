"""
Test script to validate the responsive design of Flora Balance Viewer.
This script opens the HTML file in different viewport sizes to ensure responsive behavior.
"""

import asyncio
from playwright.async_api import async_playwright
import os

async def test_responsive_design():
    """Test the Flora Balance Viewer at different screen sizes."""
    
    # Test configurations for different device sizes
    test_configs = [
        {
            "name": "Desktop Large",
            "width": 1920,
            "height": 1080,
            "expected_layout": "2-column grid"
        },
        {
            "name": "Desktop",
            "width": 1200,
            "height": 800,
            "expected_layout": "2-column grid"
        },
        {
            "name": "Tablet Landscape",
            "width": 1024,
            "height": 768,
            "expected_layout": "2-column grid"
        },
        {
            "name": "Tablet Portrait",
            "width": 768,
            "height": 1024,
            "expected_layout": "1-column stack (breakpoint)"
        },
        {
            "name": "Mobile Large",
            "width": 414,
            "height": 896,
            "expected_layout": "1-column stack"
        },
        {
            "name": "Mobile Standard",
            "width": 375,
            "height": 812,
            "expected_layout": "1-column stack"
        },
        {
            "name": "Mobile Small",
            "width": 360,
            "height": 640,
            "expected_layout": "1-column stack"
        },
        {
            "name": "Mobile Compact",
            "width": 320,
            "height": 568,
            "expected_layout": "1-column compact"
        }
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Get the absolute path to the HTML file
        html_file_path = os.path.abspath("flora_balance_viewer.html")
        file_url = f"file://{html_file_path}"
        
        print(f"🌸 Testing Flora Balance Viewer Responsive Design")
        print(f"📄 HTML file: {html_file_path}")
        print(f"🔗 URL: {file_url}")
        print("-" * 60)
        
        try:
            await page.goto(file_url)
            
            for config in test_configs:
                print(f"📱 Testing {config['name']} ({config['width']}x{config['height']})")
                
                # Set viewport size
                await page.set_viewport_size({
                    "width": config['width'],
                    "height": config['height']
                })
                
                # Wait for any CSS transitions to complete
                await page.wait_for_timeout(500)
                
                # Check if the page loaded correctly
                title = await page.title()
                if title != "Flora Balance Viewer":
                    print(f"❌ Failed: Page title is '{title}', expected 'Flora Balance Viewer'")
                    continue
                
                # Check if essential elements are visible
                try:
                    # Check header
                    header = page.locator('h1:has-text("Flora Balance Viewer")')
                    await header.wait_for(state="visible", timeout=1000)
                    
                    # Check main content sections
                    overall_eval = page.locator('h2:has-text("総合評価")')
                    await overall_eval.wait_for(state="visible", timeout=1000)
                    
                    comparison = page.locator('h2:has-text("理想の状態とあなたの状態")')
                    await comparison.wait_for(state="visible", timeout=1000)
                    
                    cst_analysis = page.locator('h2:has-text("CST分析結果")')
                    await cst_analysis.wait_for(state="visible", timeout=1000)
                    
                    # Check if content grid adapts properly
                    content_grid = page.locator('.content-grid')
                    grid_style = await content_grid.evaluate('element => getComputedStyle(element).gridTemplateColumns')
                    
                    if config['width'] <= 768:
                        # Should be single column on mobile/tablet
                        if 'fr' in grid_style and grid_style.count('fr') == 1:
                            layout_status = "✅ Single column layout"
                        else:
                            layout_status = f"⚠️  Layout may not be optimal: {grid_style}"
                    else:
                        # Should be two columns on desktop
                        if 'fr' in grid_style and grid_style.count('fr') == 2:
                            layout_status = "✅ Two column layout"
                        else:
                            layout_status = f"⚠️  Layout may not be optimal: {grid_style}"
                    
                    print(f"   {layout_status}")
                    print(f"   📐 Grid style: {grid_style}")
                    
                    # Check font sizes for readability
                    header_font_size = await page.locator('h1').evaluate('element => getComputedStyle(element).fontSize')
                    print(f"   🔤 Header font size: {header_font_size}")
                    
                    print(f"   ✅ All essential elements visible")
                    
                except Exception as e:
                    print(f"   ❌ Error checking elements: {str(e)}")
                
                print()
            
            print("🎉 Responsive design testing completed!")
            
        except Exception as e:
            print(f"❌ Failed to load page: {str(e)}")
            print("💡 Make sure the HTML file exists and is accessible")
        
        finally:
            await browser.close()

def validate_css_media_queries():
    """Validate that the CSS contains proper media queries."""
    
    print("🔍 Validating CSS Media Queries...")
    
    try:
        with open("flora_balance_viewer.html", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential media queries
        media_queries = [
            "@media (max-width: 768px)",
            "@media (max-width: 480px)", 
            "@media (max-width: 360px)"
        ]
        
        for query in media_queries:
            if query in content:
                print(f"   ✅ Found: {query}")
            else:
                print(f"   ❌ Missing: {query}")
        
        # Check for responsive grid changes
        responsive_patterns = [
            "grid-template-columns: 1fr",
            "flex-direction: column",
            "width: 100%"
        ]
        
        found_patterns = []
        for pattern in responsive_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        print(f"   📱 Responsive patterns found: {len(found_patterns)}")
        for pattern in found_patterns:
            print(f"      - {pattern}")
        
        print("✅ CSS validation completed!")
        
    except FileNotFoundError:
        print("❌ HTML file not found!")
    except Exception as e:
        print(f"❌ Error validating CSS: {str(e)}")

if __name__ == "__main__":
    print("🧪 Starting Flora Balance Viewer Tests\n")
    
    # Validate CSS first
    validate_css_media_queries()
    print()
    
    # Run responsive design tests
    asyncio.run(test_responsive_design())