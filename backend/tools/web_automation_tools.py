import json
from pathlib import Path
from langchain.tools import tool
from typing import Optional
from pydantic import BaseModel
from selenium.webdriver.remote.webdriver import WebDriver
from backend.tools.selenium_tools import (
    launch_browser,
    click_element,
    type_text,
    select_dropdown,
    check_checkbox,
    read_text,
    read_table,
    get_attribute,
    inspect_dom,
    find_element,
    wait_for_element,
    get_element_details,
    query_dom_chunk
)
from backend.utils.logger import get_logger

class Settings(BaseModel):
    max_elements: int = 100
    loop_limit: int = 20
    wait_time: int = 10
    debug_mode: bool = False
    auto_screenshot: bool = False
    headless_mode: bool = False

class LaunchBrowserArgs(BaseModel):
    url: str

class ClickElementArgs(BaseModel):
    selector_type: str
    selector: str

class TypeTextArgs(BaseModel):
    selector_type: str
    selector: str
    text: str

class SelectDropdownArgs(BaseModel):
    selector_type: str
    selector: str
    option: str
    option_type: str

class ReadTextArgs(BaseModel):
    selector_type: str
    selector: str

class InspectDomArgs(BaseModel):
    url: str
    max_elements: int = 1000

class FindElementArgs(BaseModel):
    url: str 
    tag: Optional[str]
    text: Optional[str]
    name: Optional[str]
    id: Optional[str]

class CheckCheckboxArgs(BaseModel):
    selector_type: str
    selector: str

class GetElementDetailsArgs(BaseModel):
    selector_type: str
    selector: str

class ReadTableArgs(BaseModel):
    selector_type: str
    selector: str

class GetAttributeArgs(BaseModel):
    selector_type: str
    selector: str
    attribute_name: str

class WaitForElementArgs(BaseModel):
    selector_type: str
    selector: str
    condition: str = "visible"

class QueryDomChunkArgs(BaseModel):
    url: str
    limit: Optional[int] = 20
    offset: Optional[int] = 0
    filters: Optional[dict] = None

def load_settings() -> Settings:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        return Settings(**data)
    return Settings()

def save_settings(settings: Settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)

SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"

logger = get_logger(__name__)

driver: WebDriver | None = None

CURRENT_SETTINGS: Settings = load_settings()

@tool("launch_browser", args_schema=LaunchBrowserArgs)
async def launch_browser_tool(url: str, **kwargs) -> str:
    """
        Launches a new browser session controlled by the automation agent.
        Use this as the first step before interacting with any webpage.
        The browser will remain active for subsequent actions until closed.
    """
    global driver
    try:
        driver = await launch_browser(url, CURRENT_SETTINGS.headless_mode, CURRENT_SETTINGS.wait_time)
        return f"Browser launched and navigated to {url}"
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        return f"Error launching browser: {e}"

@tool("click_element", args_schema=ClickElementArgs)
async def click_element_tool(selector_type: str, selector: str, **kwargs) -> str:
    """
        Clicks a web element on the currently loaded page.
        Use this when you want to simulate a button click, link press, or interactive element activation.
        Requires a valid selector (CSS or XPath).
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        await click_element(driver, selector_type, selector, CURRENT_SETTINGS.wait_time)
        return f"Clicked element {selector}"
    except Exception as e:
        logger.error(f"Failed to click element {selector}: {e}")
        return f"Error clicking element: {e}"

@tool("type_text", args_schema=TypeTextArgs)
async def type_text_tool(selector_type: str, selector: str, text: str, **kwargs) -> str:
    """
        Types text into an input, textarea, or editable element.
        Set `clear_first=True` to erase existing text before typing.
        Use this for search fields, login forms, or any text entry boxes.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        await type_text(driver, selector_type, selector, text, CURRENT_SETTINGS.wait_time)
        return f"Typed '{text}' into {selector}"
    except Exception as e:
        logger.error(f"Failed to type text to element {selector}: {e}")
        return f"Error typing text to element: {e}"

@tool("select_dropdown", args_schema=SelectDropdownArgs)
async def select_dropdown_tool(selector_type: str, selector: str, option: str, option_type: str, **kwargs) -> str:
    """
        Selects an option from a dropdown (select element) by value or visible text.
        Use this to choose from dropdown menus such as country, category, etc.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        await select_dropdown(driver, selector_type, selector, option, option_type, CURRENT_SETTINGS.wait_time)
        return f"Selected '{option}' from dropdown {selector}"
    except Exception as e:
        logger.error(f"Failed to select item from dropdown element {selector}: {e}")
        return f"Error selecting item from dropdown element: {e}"

@tool("read_text", args_schema=ReadTextArgs)
async def read_text_tool(selector_type: str, selector: str, **kwargs) -> str:
    """
        Reads and returns the visible text content of an element.
        Useful for extracting labels, messages, or results displayed on the page.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        text = await read_text(driver, selector_type, selector, CURRENT_SETTINGS.wait_time)
        return f"Read text from element: {text}"
    except Exception as e:
        logger.error(f"Failed to read text from element {selector}: {e}")
        return f"Error reading text from element: {e}"

@tool("inspect_dom", args_schema=InspectDomArgs)
async def inspect_dom_tool(url:str, **kwargs) -> list[dict] | str:
    """
        Use this tool when you need to explore or understand the structure of the web page,
        or if you are unsure where elements are located. This returns a list of simplified elements.
        Use it when the page has just changed or before interacting for the first time.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        elements = await inspect_dom(driver, url, CURRENT_SETTINGS.max_elements)
        if elements is None:
            elements = []
        return elements
    except Exception as e:
        logger.error(f"Failed to inspect DOM: {e}")
        return f"Error while inspecting DOM: {str(e)}"
    
@tool("find_element", args_schema=FindElementArgs)
async def find_element_tool(url: str, tag: Optional[str] = None, text: Optional[str] = None, name: Optional[str] = None, id: Optional[str] = None) -> dict | str:
    """
        Use this tool when you already know what element you are looking for,
        and want to quickly retrieve it from the cached DOM or live lookup.
        This is more efficient and should be used after an 'inspect_dom' call.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    try:
        element = await find_element(driver, url, tag, text, name, id)
        if element is None:
            return "No Matching element found."
        return element
    except Exception as e:
        logger.error(f"Failed to find element: {e}")
        return f"Error while finding element: {str(e)}"

@tool("query_dom_chunk", args_schema=QueryDomChunkArgs)
async def query_dom_chunk_tool(url: str, limit: int = 20, offset: int = 0, filters: dict | None = None) -> list[dict] | str:
    """
    Retrieve a chunk of DOM elements from the cached page.

    Use this after calling `inspect_dom` to get the actual elements 
    (in chunks) without exceeding the token limit.

    You can optionally apply filters such as `tag`, `text`, `id`, or `name`
    to narrow down the search. Use `offset` to paginate through the element list.

    Example usage:
    - Get first 20 elements: {"url": "...", "limit": 20}
    - Get next 20 elements: {"url": "...", "limit": 20, "offset": 20}
    - Filter by text: {"url": "...", "filters": {"text": "Sign up"}}
    - Filter by tag: {"url": "...", "filters": {"tag": "button"}}
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    try:
        element = await query_dom_chunk(url, limit, offset, filters)
        if element is None:
            return "No Matching element found."
        return element
    except Exception as e:
        logger.error(f"Failed to query DOM chunk: {e}")
        return f"Error while querying DOM chunk: {str(e)}"
    
    
@tool("check_checkbox", args_schema=CheckCheckboxArgs)
async def check_checkbox_tool(selector_type: str, selector: str, **kwargs) -> str:
    """
        Checks or unchecks a checkbox element to match the desired state.
        Use this when you need to toggle options, preferences, or filters.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        await check_checkbox(driver, selector_type, selector, CURRENT_SETTINGS.wait_time)
        return f"Checkbox {selector} has been checked"
    except Exception as e:
        logger.error(f"Failed to check checkbox {selector}: {e}")
        return f"Error checking checkbox: {e}"

@tool("read_table", args_schema=ReadTableArgs)
async def read_table_tool(selector_type: str, selector: str, **kwargs) -> list[dict] | str:
    """
        Reads a table element and returns its contents as a list of dictionaries.
        Each dictionary represents a row, mapping column headers to cell values.
        Use this for structured data extraction.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        table_data = await read_table(driver, selector_type, selector, CURRENT_SETTINGS.wait_time)
        return table_data
    except Exception as e:
        logger.error(f"Failed to read table {selector}: {e}")
        return f"Error reading table: {e}"
    
@tool("get_element_details", args_schema=GetElementDetailsArgs)
async def get_element_details_tool(selector_type: str, selector: str, **kwargs) -> dict | str:
    """
        Gets element details.
        Use this to get input value, or select option items.
        returns dict of element details
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        element_details = await get_element_details(driver, selector_type, selector, CURRENT_SETTINGS.wait_time)
        return element_details
    except Exception as e:
        logger.error(f"Failed to get element details {selector}: {e}")
        return f"Error  getting element details: {e}"
    
@tool("get_attribute", args_schema=GetAttributeArgs)
async def get_attribute_tool(selector_type: str, selector: str, attribute_name: str, **kwargs) -> str:
    """
        Retrieves the value of a specific HTML attribute (e.g., href, src, value, title).
        Use this when you need metadata or hidden information from an element.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        value = await get_attribute(driver, selector_type, selector, attribute_name, CURRENT_SETTINGS.wait_time)
        return value
    except Exception as e:
        logger.error(f"Failed to get attribute from element {selector}: {e}")
        return f"Error getting attribute from element: {e}"
    
@tool("wait_for_element", args_schema=WaitForElementArgs)
async def wait_for_element_tool(selector_type: str, selector: str, condition: str = "visible", **kwargs) -> str:
    """
        Waits for an element to satisfy a given condition before continuing.
        Conditions: 'visible', 'clickable', or 'present'.
        Use this to ensure dynamic elements have loaded before interaction.
    """
    if not driver:
        return "Browser not initialized. Please call launch_browser first."
    
    try:
        await wait_for_element(driver, selector_type, selector, condition, CURRENT_SETTINGS.wait_time)
        return f"Element {selector} satisfied condition '{condition}'"
    except Exception as e:
        logger.error(f"Failed while waiting for element {selector} to satisfy condition: '{condition}': {e}")
        return f"Error waiting for element to satisfy condition: '{condition}': {e}"
    
selenium_toolkit = [
    launch_browser_tool,
    click_element_tool,
    type_text_tool,
    select_dropdown_tool,
    read_text_tool,
    inspect_dom_tool,
    check_checkbox_tool,
    read_table_tool,
    get_attribute_tool,
    wait_for_element_tool,
    find_element_tool,
    get_element_details_tool,
    query_dom_chunk_tool
    ]

TOOLS_REGISTRY = {
    "launch_browser": launch_browser_tool,
    "click_element": click_element_tool,
    "type_text": type_text_tool,
    "select_dropdown": select_dropdown_tool,
    "read_text": read_text_tool,
    "inspect_dom": inspect_dom_tool,
    "check_checkbox": check_checkbox_tool,
    "read_table": read_table_tool,
    "get_attribute": get_attribute_tool,
    "wait_for_element": wait_for_element_tool,
    "find_element": find_element_tool,
    "get_element_details": get_element_details_tool,
    "query_dom_chunk": query_dom_chunk_tool
}