import asyncio
import time
from rapidfuzz import fuzz
from selenium import webdriver
from typing import Optional
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from backend.db.crud import get_or_create_dom_page, add_dom_elements, get_dom_elements_by_page_id
from backend.utils.logger import get_logger


logger = get_logger(__name__)

TAGS_TO_INCLUDE = {"a", "button", "input", "textarea", "select", "label", "form", "img", "table", "span"}

DOM_CACHE: dict[str, list[dict]] = {}

async def generate_css_selector(elem, driver: WebDriver):
    """
        Generates a CSS selector for an element if possible
        This prioritizes id > class > name > fallback to tag
    """
    tag = elem.tag_name.lower()
    elem_id = elem.get_attribute("id")
    elem_class = elem.get_attribute("class")
    name = elem.get_attribute("name")

    selector = None

    if elem_id:
        selector = f"#{elem_id}"
    elif elem_class:
        classes = ".".join(cls for cls in elem_class.split() if cls)
        selector = f"{tag}.{classes}"
    elif name:
        selector = f"{tag}[name='{name}']"

    if selector:
        matches = driver.find_elements("css selector", selector)
        if len(matches) == 0:
            selector = None
    
    return selector

async def inspect_dom(driver: WebDriver, url: str, max_elements: int = 1000):
    """
        This gets the JSON representation of interactive elements of the web page.
        This caches the result per page URL
    """

    page = await get_or_create_dom_page(url)

    logger.info("start inspect dom")

    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//Input | //button | //a"))
        )
        time.sleep(5)
        logger.info("[inspect_dom] DOM ready with visible elements.")
    except Exception as e:
        logger.warning(f"[inspect_dom] timed out waiting for DOM readiness: {e}")


    elements_info = []
    all_elements = driver.find_elements(By.XPATH, "//*")

    for i, elem in enumerate(all_elements):
        if len(elements_info) >= max_elements:
            break
        
        #await higlight_element(driver, elem, color="red", border=2, duration=1.0)

        tag = elem.tag_name.lower()
        if tag not in TAGS_TO_INCLUDE:
            continue

        if not elem.is_displayed() or not elem.is_enabled():
            continue

        try:
            css_selector = await generate_css_selector(elem, driver)

            xpath = None
            if not css_selector:
                try:
                    xpath = driver.execute_script(
                        "function absoluteXPath(element) {"
                        "var comps = [], parent = null; var getPos = function(e){"
                        "var pos = 1; for(var cur=e.previousSibling; cur; cur=cur.previousSibling){"
                        "if(cur.nodeName==e.nodeName) pos++;} return pos;};"
                        "for(; element && !(element instanceof Document); element=element.parentNode){"
                        "comps.push({name: element.nodeName.toLowerCase(), pos: getPos(element)});}"
                        "var xpath=''; for(var i=comps.length-1;i>=0;i--){"
                        "xpath+='/'+comps[i].name+'['+comps[i].pos+']';} return xpath;}"
                        "return absoluteXPath(arguments[0]);", elem)
                except Exception:
                    xpath = None
        
            selector_type = "css" if css_selector else "xpath"
            selector = css_selector or xpath
            if not selector:
                continue

            info = {
                "tag": tag,
                "id": elem.get_attribute("id"),
                "name": elem.get_attribute("name"),
                "text": elem.text.strip()[:80],
                "visible": elem.is_displayed(),
                "enabled": elem.is_enabled(),
                "selector_type": selector_type,
                "selector": selector
            }

            if tag == "input":
                info.update({
                    "type": elem.get_attribute("type"),
                    "placeholder": elem.get_attribute("placeholder"),
                })
            elif tag == "textarea":
                info.update({
                    "placeholder": elem.get_attribute("placeholder")
                })
            elif tag == "select":
                info.update({
                    "options_count": len(elem.find_elements(By.TAG_NAME, "option"))
                })
            elif tag == "a":
                info.update({"href": elem.get_attribute("href")})
            elif tag == "button":
                info.update({
                    "type": elem.get_attribute("type"),
                    "value": elem.get_attribute("value")
                })
            elif tag == "form":
                info.update({
                    "action": elem.get_attribute("action"),
                    "method": elem.get_attribute("method")
                })

            elements_info.append(info)
            
        except Exception as e:
            logger.warning("Skipping element %s due to unexpected error: %s", e)
            continue
    
    await add_dom_elements(page.id, elements_info)

    elements_found = f"Number of elements that are displayed and enabled found: {len(elements_info)}"
    
    return elements_found

async def find_element(driver: WebDriver, url: str, tag: Optional[str] = None, text: Optional[str] = None, name: Optional[str] = None, id: Optional[str] = None) -> dict | None:
    """
        Finds a signle element in cached DOM or live if not cached.
        Returns a minimal JSON for the agent
    """
    page = await get_or_create_dom_page(url)

    elements = await get_dom_elements_by_page_id(page.id)

    for elem in elements:
        if tag and elem.tag != tag:
            continue
        if id and elem.id != id:
            continue
        if name and elem.name != name:
            continue
        if text and text not in (elem.text or ""):
            continue
        
        return {
            "tag": elem.tag,
            "id": elem.id,
            "name": elem.name,
            "text": elem.text,
            "visible": elem.visible,
            "enabled": elem.enabled,
            "selector_type": elem.selector_type,
            "selector": elem.selector
        }
    
    return None

async def get_element_details(driver: WebDriver, selector_type: str, selector: str, wait_time: int = 10):
    """
        Click element based on selector safely after waiting for it to be visible and clickable
    """
    logger.info("start get element details")
    def _get_element_details():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "clickable", wait_time))
            tag = element.tag_name.lower()
            details = {}

            if tag == "select":
                options = element.find_elements(By.TAG_NAME, "option")
                details["options"] = [{"text": o.text, "value": o.get_attribute("value")} for o in options[:10]]
            elif tag == "input":
                details["value"] = element.get_attribute("value")
            
            return details
        except TimeoutException:
            logger.error(f"Element not found or not clickable within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to click element {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_get_element_details)

async def higlight_element(driver, element, color="red", border=2, duration=1.0):
    """
        This function highlights selenium elements by adding a colored border for a short duration

        Parameters:
        -driver: Selenium Webdriver
        -element: WebElement to highlight
        -color: border color
        -border: border width in pixels
        -duration: how long to keep the highlight
    """
    logger.info("start highlight element")
    original_style = element.get_attribute("style")

    driver.execute_script(
        "arguments[0].setAttribute('style', arguments[1]);",
        element,
        f"border: {border}px solid {color}; {original_style}"
        )

    if duration > 0:
        import time
        time.sleep(duration)

    driver.execute_script(
        "arguments[0].setAttribute('style', arguments[1]);",
        element,
        original_style
        )

async def launch_browser(url: str, headless: bool = False, wait_time: int = 10):
    """
        Launch browser and navigate to the given url
        return:
            -WebDriver instance
    """
    logger.info("start launch browser")
    def _launch():
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            return driver
        except WebDriverException as e:
            logger.error(f"Failed to launch Chrome: {e}")
            raise
    
    driver = await asyncio.to_thread(_launch)

    try:
        await asyncio.to_thread(
            lambda: WebDriverWait(driver, wait_time).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
            )
        )
    except Exception as e:
        logger.warning(f"Page did not fully load within {wait_time}s: {e}")
    
    return driver

async def click_element(driver: WebDriver, selector_type: str, selector: str, wait_time: int = 10):
    """
        Click element based on selector safely after waiting for it to be visible and clickable
    """
    logger.info("start click element")
    def _click():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "clickable", wait_time))
            element.click()
            return True
        except TimeoutException:
            logger.error(f"Element not found or not clickable within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to click element {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_click)

async def type_text(driver: WebDriver, selector_type: str, selector: str, text: str, wait_time: int = 10, clear_first: bool = True):
    """
        Type text into an input or textarea element safely after waiting for it to be visible
    """
    logger.info("start type text")
    def _type():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "visible", wait_time))

            if clear_first:
                element.clear()
            
            element.send_keys(text)

            return True
        except TimeoutException:
            logger.error(f"Element not found or not visible within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to type text to element {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_type)

async def select_dropdown(driver: WebDriver, selector_type: str, selector: str, option: Optional[str] = None, option_type: str = "text", wait_time: int = 10):
    """
        Select an option in a <select> element safely after waiting for it to be visible
    """
    logger.info("start select dropdown")
    def _select():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "visible", wait_time))

            select = Select(element)

            if option is None:
                raise ValueError("Option cannot be None when selecting an item from dropdown")

            if option_type == "text":
                select.select_by_visible_text(option)
            elif option_type == "value":
                select.select_by_value(option)
            elif option_type == "index":
                select.select_by_index(int(option))
            else:
                raise ValueError(f"Invalid option_type: {option_type}")
            
            return True
        except TimeoutException:
            logger.error(f"Element not found or not visible within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to select item from element {selector}: {e}")
            raise
        except ValueError as ve:
            logger.error(ve)
            raise
        
    return await asyncio.to_thread(_select)

async def check_checkbox(driver: WebDriver, selector_type: str, selector: str, wait_time: int = 10):
    """
        Checks a checkbox safely after waiting for it to be clickable
    """
    logger.info("start check checkbox")
    def _check():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "clickable", wait_time))

            if not element.is_selected():
                element.click()
            return True
        except TimeoutException:
            logger.error(f"Element not found or not clickable within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to click element {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_check)

async def read_text(driver: WebDriver, selector_type: str, selector: str, wait_time: int = 10) -> str:
    """
        Read text from an element safely after waiting for it to be visible
    """
    logger.info("start read text")
    def _read():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "visible", wait_time))
            return element.text.strip()
        except TimeoutException:
            logger.error(f"Element not found or not visible within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to read text of element {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_read)

async def read_table(driver: WebDriver, selector_type: str, selector: str, wait_time: int=10) -> list[dict]:
    """
        Read element table and  return as list of dict where each dict represents a row with column headers as keys safely after waiting for it to be visible
    """
    logger.info("start read table")
    def _read():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "visible", wait_time))

            headers = [th.text.strip() for th in element.find_elements(By.TAG_NAME, "th")]
            if not headers:
                first_row = element.find_elements(By.TAG_NAME, "tr")[0]
                headers = [td.text.strip() for td in first_row.find_elements(By.TAG_NAME, "td")]
            
            rows = []
            for tr in element.find_elements(By.TAG_NAME, "tr")[1:]:
                cells = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]
                if len(cells) == len(headers):
                    rows.append(dict(zip(headers, cells)))
                else:
                    rows.append({f"col_{i}": cell for i, cell in enumerate(cells)})
            
            logger.info(f"Read table with {len(rows)} rows and {len(headers)} columns.")

            return rows
    
        except TimeoutException:
            logger.error(f"Table not found or not visible within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to read table {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_read)

async def get_attribute(driver: WebDriver, selector_type: str, selector: str, attribute_name: str, wait_time: int =10) -> str:
    """
        Retrieve the value of a specific attribute from an element safely after waiting for it to be present
    """
    logger.info("start get attribute")
    def _get_attribute():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = asyncio.run(wait_for_element(driver, selector_type, selector, "present", wait_time))
            value = element.get_attribute(attribute_name)
            if value is None:
                raise ValueError(f"Attribute '{attribute_name}' not found in element: {selector}")
            return value.strip() if isinstance(value, str) else value
        except TimeoutException:
            logger.error(f"Element not found or not present within {wait_time}s: {selector}")
            raise
        except WebDriverException as e:
            logger.error(f"Failed to retrieve attribute '{attribute_name}' from {selector}: {e}")
            raise
    
    return await asyncio.to_thread(_get_attribute)

async def wait_for_element(driver: WebDriver, selector_type: str, selector: str, condition: str = "visible", wait_time: int = 10) -> WebElement:
    """
        Wait for element to be in a certain condition before proceeding
    """
    logger.info("start wait for element")
    def _wait():
        try:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            wait = WebDriverWait(driver, wait_time)

            if condition == "visible":
                return wait.until(EC.visibility_of_element_located((by, selector)))
            elif condition == "clickable":
                return wait.until(EC.element_to_be_clickable((by, selector)))
            elif condition == "present":
                return wait.until(EC.presence_of_element_located((by, selector)))
            else:
                raise ValueError(f"Unknown condition type: {condition}")
        except TimeoutException:
            logger.error(f"Timeout: element not {condition} within {wait_time}: {selector}")
            raise
    
    return await asyncio.to_thread(_wait)

async def query_dom_chunk(url: str, limit: int = 50, offset: int = 0, filters: dict | None = None) -> list[dict] | None:
    """
        Returns a chunk of cached DOM elements as a list of dicts.
        Optional fuzzy filtering (text, tag, id, name)
    """
    page = await get_or_create_dom_page(url)

    elements = await get_dom_elements_by_page_id(page.id)

    if not elements:
        return None
    
    if filters:
        if "tag" in filters:
            elements = [e for e in elements if e.tag and e.tag.lower() == filters["tag"].lower()]
        
        if "text" in filters:
            query_text = filters["text"].lower()
            elements = [e for e in elements if e.text and fuzz.partial_ratio(query_text, e.text.lower()) > 80]
        
        if "id" in filters:
            query_id = filters["id"].lower()
            elements = [e for e in elements if e.element_id and fuzz.partial_ratio(query_id, e.element_id.lower()) > 85]
        
        if "name" in filters:
            query_name = filters["name"].lower()
            elements = [e for e in elements if e.name and fuzz.partial_ratio(query_name, e.name.lower()) > 85]
    
    chunk = elements[offset: offset + limit]

    chunk_dicts = []

    for i, elem in enumerate(chunk, start=offset):
        chunk_dicts.append({
            "idx": i,
            "tag": elem.tag,
            "id": elem.element_id,
            "name": elem.name,
            "text": elem.text,
            "visible": elem.visible,
            "enabled": elem.enabled,
            "selector_type": elem.selector_type,
            "selector": elem.selector
        })

    return chunk_dicts