import json
import sys
import time
from datetime import datetime
from seleniumbase import SB
from bs4 import BeautifulSoup

def scrape_business_info(control_number):
    with SB(uc=True, test=True, locale="en", maximize=True, xvfb=True) as sb:
        url = "https://tncab.tnsos.gov/business-entity-search"
        sb.activate_cdp_mode(url)

        sb.cdp.sleep(5)

        # Open site and bypass Cloudflare/captcha
        input_selector = 'input[data-val-property-name="Filenumber"]'
        search_button = 'button[data-val-tooltip="Search"]'
        
        # Handle captcha if needed with timeout
        start_time = time.time()
        timeout_seconds = 30
        
        while not sb.cdp.is_element_visible(search_button):
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                print(f"Captcha handling exceeded {timeout_seconds} seconds - exiting")
                sys.exit(1)
                
            try:
                # Scroll to bring captcha into view
                sb.cdp.scroll_into_view('div[id*="recaptcha"]')
                
                # Get captcha coordinates and click
                rect = sb.cdp.get_gui_element_rect('div[id*="recaptcha"]')
                x = rect['x'] + 35
                y = rect['y'] + 20
                
                # Click captcha directly at calculated coordinates
                sb.cdp.gui_click_x_y(x, y)
                sb.cdp.sleep(1)
                
            except Exception as e:
                print(f"Captcha attempt failed: {e}")
                sb.cdp.sleep(1)

        # Input the control number and search
        sb.cdp.type(input_selector, control_number)
        sb.cdp.click(search_button)
        
        # Wait for search results and click Details button
        details_button = 'button[title="Details"]'
        sb.cdp.click(details_button)
        
        # Wait for business details page to load
        business_details_selector = 'div[id="business-details"]'
        while not sb.cdp.is_element_present(business_details_selector):
            sb.cdp.sleep(0.1)
        
        # Extract the business details div
        html = sb.cdp.get_page_source()
        soup = BeautifulSoup(html, "html.parser")
        business_details_div = soup.find("div", {"id": "business-details"})
        
        if business_details_div:
            data = {}
            
            # Extract business name (h2 element)
            business_name = business_details_div.find("h2")
            if business_name:
                data["Business Name"] = business_name.get_text(strip=True)
            
            # Extract all h4 elements with business information
            h4_elements = business_details_div.find_all("h4")
            
            for h4 in h4_elements:
                text = h4.get_text(strip=True)
                if ":" in text:
                    key, value = text.split(":", 1)
                    data[key.strip()] = value.strip()
            
            # Extract address information from the structured divs
            address_sections = business_details_div.find_all("div", class_="col-md-4")
            
            for section in address_sections:
                h4_with_underline = section.find("h4", style="text-decoration:underline")
                if h4_with_underline:
                    section_title = h4_with_underline.get_text(strip=True)
                    address_h4s = section.find_all("h4")[1:]  # Skip the title h4
                    address_lines = [h4.get_text(strip=True) for h4 in address_h4s if h4.get_text(strip=True)]
                    
                    if section_title == "Registered Agent":
                        data["Registered Agent"] = {
                            "Name": address_lines[0] if len(address_lines) > 0 else "",
                            "Address": " ".join(address_lines[1:]) if len(address_lines) > 1 else ""
                        }
                    elif section_title == "Principal Office Address":
                        data["Principal Office Address"] = " ".join(address_lines)
                    elif section_title == "Mailing Address":
                        data["Mailing Address"] = " ".join(address_lines)
            
            # Extract standing information
            standing_row = business_details_div.find("div", style="border: 1px solid #e4e7eb;margin: 0 0 10px 0;")
            if standing_row:
                standing_h4s = standing_row.find_all("h4")
                for h4 in standing_h4s:
                    text = h4.get_text(strip=True)
                    if ":" in text:
                        key, value = text.split(":", 1)
                        data[key.strip()] = value.strip()
            
            # Save to JSON file with dynamic filename
            output_filename = f"business_info_{control_number}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully extracted data and saved to {output_filename}")
                
        else:
            print("Could not find business details div")
        
        print(f"Successfully processed control number {control_number}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tennessee_scraper_clean.py <control_number>")
        sys.exit(1)
    control_number_arg = sys.argv[1]
    scrape_business_info(control_number_arg) 
