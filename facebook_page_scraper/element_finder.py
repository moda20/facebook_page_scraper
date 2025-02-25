#!/usr/bin/env python3
import datetime
import logging
import re
import sys
import time
import traceback
import urllib.request
from urllib.parse import urlparse, parse_qs

import dateutil
from dateutil.parser import parse
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .driver_utilities import Utilities
from .scraping_utilities import Scraping_utilities

logger = logging.getLogger(__name__)
format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(format)
logger.addHandler(ch)


class Finder:
    """
    Holds the collections of methods that finds element of the facebook's posts using selenium's webdriver's methods
    """

    @staticmethod
    def __get_status_link(link_list):
        status = ""
        for link in link_list:
            link_value = link.get_attribute("href")
            if "/posts/" in link_value and "/groups/" in link_value:
                status = link
                break
            if "/posts/" in link_value:
                status = link
                break
            if "/videos/pcb" in link_value:
                status = link
                break
            elif "/photos/" in link_value:
                status = link
                break
            if "fbid=" in link_value:
                status = link
                break
            elif "/group/" in link_value:
                status = link
                break
            if "/videos/" in link_value:
                status = link
                break
            elif "/groups/" in link_value:
                status = link
                break
        return status

    @staticmethod
    def __find_status(post, layout, isGroup, driver, page_or_group_name, single_post = False):
        """finds URL of the post, then extracts link from that URL and returns it"""
        try:
            link = None
            status_link = None
            status = None

            if layout == "old":
                # aim is to find element that looks like <a href="URL" class="_5pcq"></a>
                # after finding that element, get it's href value and pass it to different method that extracts post_id from that href
                status_link = post.find_element(By.CLASS_NAME, "_5pcq").get_attribute(
                    "href"
                )
                logger.debug("old link layouut\n")
                # extract out post id from post's url
                status = Scraping_utilities._Scraping_utilities__extract_id_from_link(
                    status_link
                )
            elif layout == "new":
                driver.execute_script("arguments[0].scrollIntoView({ block: 'center', inline: 'center'});", post)
                # try to hover over the time link
                link = Utilities._Utilities__find_with_multiple_selectors(post, [
                    'span > a[attributionsrc][role="link"][href*="/posts/"]',
                    'span > a[attributionsrc][role="link"][href*="/permalink"]',
                    'span > a[attributionsrc][role="link"][href="#"]',
                    'span > a[role="link"]' if isGroup else 'span > a[target="_blank"][role="link"]',
                ])
                actions = ActionChains(driver)
                if single_post:
                    driver.execute_script("arguments[0].scrollIntoView();", link)
                else:
                    # scroll to the link
                    scrolling_script = """
                        const element = arguments[0];
                        const elementRect = element.getBoundingClientRect();
                        const absoluteElementTop = elementRect.top + window.pageYOffset;
                        const middle = absoluteElementTop - (window.innerHeight / 2);
                        window.scrollTo(0, middle); 
                    """
                    driver.execute_script(scrolling_script, link)
                Utilities._Utilities__close_force_login_popup(driver)
                driver.execute_script("arguments[0].style.border='2px solid black'", link);
                actions.move_to_element(link).perform()
                Utilities._Utilities__close_force_login_popup(driver)
                time.sleep(2)

                # actually not  useful to trigger the hover witht he mouse event
                # should be deleted in the future
                javaScript = """
                    var evObj = document.createEvent('MouseEvents');
                    evObj.initMouseEvent(\"mouseover\",true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                    arguments[0].dispatchEvent(evObj);
                """
                driver.execute_script(javaScript, link)
                try:
                    link = post.find_element(
                        By.CSS_SELECTOR,
                        'span > a[role="link"]' if isGroup else 'span > a[href*="/posts/"][role="link"]'
                    )
                except NoSuchElementException:
                    postId = Finder._Finder__find_post_id(post, layout)
                    if postId is not None:
                        post_url = "https://www.facebook.com/{}/posts/{}".format(page_or_group_name, postId)
                        print("constructed post Url ")
                        print(post_url)
                        return (postId, post_url, link)

                Utilities._Utilities__close_force_login_popup(driver)
                if link is not None:
                    status_link = link.get_attribute("href")
                    status = Scraping_utilities._Scraping_utilities__extract_id_from_link(
                        status_link
                    )
                    if not isGroup and status_link and status:  # early exit for non group
                        return (status, status_link, link)

                links = post.find_elements(By.TAG_NAME, 'a')
                if links:
                    # Initialize variables to store the matching link element and URL
                    matching_link_element = None
                    post_url = None

                    # Iterate over links to find the first one that matches the criteria
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/groups/' in href:
                            post_url = href  # Store the URL
                            matching_link_element = link  # Store the link element
                            break  # Exit the loop after finding the first match

                    # Check if a matching link was found
                    if post_url and matching_link_element:
                        status = Scraping_utilities._Scraping_utilities__extract_id_from_link(post_url)
                        # Now you have the URL, the status, and the matching link element itself
                        return (status, post_url, matching_link_element)

        except NoSuchElementException:
            # if element is not found
            status = "NA"

        except Exception as ex:
            logger.exception("Error at find_status method : {}".format(ex))
            status = "NA"
        return (status, status_link, link)



    @staticmethod
    def __find_share(post, layout):
        """finds shares count of the facebook post using selenium's webdriver's method"""
        try:
            if layout == "old":
                # aim is to find element that have datatest-id attribute as UFI2SharesCount/root
                shares = post.find_element(
                    By.CSS_SELECTOR, "._355t._4vn2"
                ).get_attribute("textContent")
                shares = Scraping_utilities._Scraping_utilities__extract_numbers(shares)
            elif layout == "new":
                element = post.find_element(
                    By.CSS_SELECTOR, 'div:nth-child(2) > span > div > div > div:nth-child(1) > span'
                )
                shares = "0"
                if not element:
                  return shares
                return element.text
            return shares
        except NoSuchElementException:
            # if element is not present that means there wasn't any shares
            shares = 0

        except Exception as ex:
            logger.exception("Error at Find Share method : {}".format(ex))
            shares = 0

        return shares

    @staticmethod
    def __find_reactions(post):
        """finds all reaction of the facebook post using selenium's webdriver's method"""
        try:
            # find element that have attribute aria-label as 'See who reacted to this
            reactions_all = post.find_element(
                By.CSS_SELECTOR, '[aria-label="See who reacted to this"]'
            )
        except NoSuchElementException:
            reactions_all = ""
        except Exception as ex:
            logger.exception("Error at find_reactions method : {}".format(ex))
        return reactions_all

    @staticmethod
    def __find_comments(post, layout):
        """finds comments count of the facebook post using selenium's webdriver's method"""
        try:
            comments = ""
            if layout == "old":
                comments = post.find_element(By.CSS_SELECTOR, "a._3hg-").get_attribute(
                    "textContent"
                )
                # extract numbers from text
                comments = Scraping_utilities._Scraping_utilities__extract_numbers(
                    comments
                )
            elif layout == "new":
                element = post.find_element(
                    By.CSS_SELECTOR, 'div:nth-child(1) > span > div > div > div:nth-child(1) > span'
                )
                comments = 0
                if element is None:
                    return comments
                return element.text
        except NoSuchElementException:
            comments = 0
        except Exception as ex:
            logger.exception("Error at find_comments method : {}".format(ex))
            comments = 0

        return comments

    @staticmethod
    def __fetch_post_passage(href):

        response = urllib.request.urlopen(href)

        text = response.read().decode("utf-8")

        post_message_div_finder_regex = (
            '<div data-testid="post_message" class=".*?" data-ft=".*?">(.*?)<\/div>'
        )

        post_message = re.search(post_message_div_finder_regex, text)

        replace_html_tags_regex = "<[^<>]+>"
        message = re.sub(replace_html_tags_regex, "", post_message.group(0))

        return message

    @staticmethod
    def __element_exists(element, css_selector):
        try:
            found = element.find_element(By.CSS_SELECTOR, css_selector)
            return True
        except NoSuchElementException:
            return False

    @staticmethod
    def __find_content(post, driver, layout):
        """finds content of the facebook post using selenium's webdriver's method and returns string containing text of the posts"""
        try:
            if layout == "old":
                post_content = post.find_element(By.CLASS_NAME, "userContent")
                # if 'See more' or 'Continue reading' is present in post
                if Finder._Finder__element_exists(
                    post_content, "span.text_exposed_link > a"
                ):
                    element = post_content.find_element(
                        By.CSS_SELECTOR, "span.text_exposed_link > a"
                    )  # grab that element
                    # if element have already the onclick function, that means it is expandable paragraph
                    if element.get_attribute("onclick"):
                        # click 'see more' button to get hidden text as well
                        Utilities._Utilities__click_see_more(driver, post_content)
                        content = (
                            Scraping_utilities._Scraping_utilities__extract_content(
                                post_content
                            )
                        )  # extract content out of it
                    # if element have attribute of target="_blank"
                    elif element.get_attribute("target"):
                        # if it does not have onclick() method, it means we'll to extract passage by request
                        # if content have attribute target="_blank" it indicates that text will open in new tab,
                        # so make a seperate request and get that text
                        content = Finder._Finder__fetch_post_passage(
                            element.get_attribute("href")
                        )
                    else:
                        content = post_content.get_attribute("textContent")
                else:
                    # if it does not have see more, just get the text out of it
                    content = post_content.get_attribute("textContent")
            elif layout == "new":
                post_content = post.find_element(
                    By.CSS_SELECTOR, '[data-ad-preview="message"]'
                )
                # if "See More" button exists
                if Finder._Finder__element_exists(
                    post_content, 'div[dir="auto"] > div[role]'
                ):
                    element = post_content.find_element(
                        By.CSS_SELECTOR, 'div[dir="auto"] > div[role]'
                    )  # grab that element
                    if element.get_attribute("target"):
                        content = Finder._Finder__fetch_post_passage(
                            element.get_attribute("href")
                        )
                    else:
                        Utilities._Utilities__click_see_more(
                            driver, post_content, 'div[dir="auto"] > div[role]'
                        )
                        content = post_content.get_attribute(
                            "innerText"
                        )  # extract content out of it
                else:
                    # if it does not have see more, just get the text out of it
                    content = post_content.get_attribute("innerText")

        except NoSuchElementException:
            # if [data-testid="post_message"] is not found, it means that post did not had any text,either it is image or video
            content = ""
        except Exception as ex:
            logger.exception("Error at find_content method : {}".format(ex))
            content = ""
        return content

    @staticmethod
    def __find_posted_time(post, layout, link_element, driver, isGroup, single_post = False):
        """finds posted time of the facebook post using selenium's webdriver's method"""
        try:
            # extract element that looks like <abbr class='_5ptz' data-utime="some unix timestamp"> </abbr>
            # posted_time = post.find_element_by_css_selector("abbr._5ptz").get_attribute("data-utime")
            if layout == "old":
                posted_time = post.find_element(By.TAG_NAME, "abbr").get_attribute(
                    "data-utime"
                )
                return datetime.datetime.fromtimestamp(float(posted_time)).isoformat()
            elif layout == "new":
                if isGroup:
                    # NOTE There is no aria_label on these link elements anymore
                    # Facebook uses a shadowDOM element to hide timestamp, which is tricky to extract
                    # An unsuccesful attempt to extract time from nested shadowDOMs is below

                    js_script = """
                        // Starting from the provided element, find the SVG using querySelector
                        var svgElement = arguments[0].querySelector('svg');

                        // Assuming we're looking for a shadow DOM inside or related to the <use> tag, which is unconventional
                        // var useElement = svgElement.querySelector('use');

                        // Placeholder for accessing the shadow DOM, which is not directly applicable to <use> tags.
                        // This step assumes there's some unconventional method to access related shadow content
                        var shadowContent;

                        // Hypothetically accessing shadow DOM or related content. This part needs adjustment based on actual structure or intent
                        // As <use> tags don't host shadow DOMs, this is speculative and might represent a different approach in practice
                        if (svgElement.shadowRoot) {
                            shadowContent = svgElement.shadowRoot.querySelector('some-element').textContent;
                        } else {
                            // Fallback or alternative method to access intended content, as direct shadow DOM access on <use> is not standard
                            shadowContent = 'Fallback or alternative content access method needed';
                        }

                        return shadowContent;
                    """
                    # Execute the script with the link_element as the argument
                    timestamp = driver.execute_script(js_script, link_element)
                    logger.debug("TIMESTAMP: " + str(timestamp))
                elif not isGroup:
                    # getting the timestamp from teh tooltip after hovering the link
                    logger.debug("getting timestamp from hovering tooltip")
                    actions = ActionChains(driver)
                    scrolling_script = """
                                            const element = arguments[0];
                                            const elementRect = element.getBoundingClientRect();
                                            const absoluteElementTop = elementRect.top + window.pageYOffset;
                                            const middle = absoluteElementTop - (window.innerHeight / 2);
                                            window.scrollTo(0, middle); 
                                        """
                    driver.execute_script(scrolling_script, link_element)
                    if single_post:
                        driver.execute_script("arguments[0].scrollIntoView();", link_element)
                    actions.move_to_element(link_element).perform()

                    parent_element = link_element.find_element_by_xpath("..")
                    parent_element_described_by=parent_element.get_attribute("aria-describedby")

                    #loop over the parent elements to find the id, in some cases the is is not on the parent but the grandparent element of the link
                    retries = 0
                    while parent_element_described_by is None and retries < 5:
                        parent_element = parent_element.find_element_by_xpath("..")
                        parent_element_described_by=parent_element.get_attribute("aria-describedby")
                        retries += 1

                    tooltipElement = driver.find_element(By.CSS_SELECTOR, f"[id*={parent_element_described_by.replace(':', '').replace(':', '')}]")
                    timestampContent = tooltipElement.get_attribute("innerText")
                    logger.debug(f"tooltipElement content : {timestampContent}")
                    timestamp = (
                        parse(timestampContent).isoformat()
                        if len(timestampContent) > 5
                        else Scraping_utilities._Scraping_utilities__convert_to_iso(
                            timestampContent
                        )
                    )
                return timestamp

        except TypeError:
            timestamp = ""
        except Exception as ex:
            logger.exception("Error at find_posted_time method : {}".format(ex))
            timestamp = ""
            return timestamp

    @staticmethod
    def __find_video_url(post):
        """finds video of the facebook post using selenium's webdriver's method"""
        try:
            # if video is found in the post, than create a video URL by concatenating post's id with page_name
            video_element = post.find_elements(By.TAG_NAME, "video")
            srcs = []
            for video in video_element:
                srcs.append(video.get_attribute("src"))
        except NoSuchElementException:
            video = []
            pass
        except Exception as ex:
            video = []
            logger.exception("Error at find_video_url method : {}".format(ex))

        return srcs

    @staticmethod
    def __find_image_url(post, layout):
        """finds all image of the facebook post using selenium's webdriver's method"""
        try:
            if layout == "old":
                # find all img tag that looks like <img class="scaledImageFitWidth img" src=""> div > img[referrerpolicy]
                images = post.find_elements(
                    By.CSS_SELECTOR, "img.scaledImageFitWidth.img"
                )
                # extract src attribute from all the img tag,store it in list
            elif layout == "new":
                images = post.find_elements(
                    By.CSS_SELECTOR, "div > img[referrerpolicy]"
                )
            sources = (
                [image.get_attribute("src") for image in images]
                if len(images) > 0
                else []
            )
        except NoSuchElementException:
            sources = []
            pass
        except Exception as ex:
            logger.exception("Error at find_image_url method : {}".format(ex))
            sources = []

        return sources

    @staticmethod
    def __find_post_id(post, layout):
        """finds all image of the facebook post using selenium's webdriver's method"""
        try:
            if layout == "old":
                # find all img tag that looks like <img class="scaledImageFitWidth img" src=""> div > img[referrerpolicy]
                images = post.find_elements(
                    By.CSS_SELECTOR, "img.scaledImageFitWidth.img"
                )
                # extract src attribute from all the img tag,store it in list
            elif layout == "new":
                images = post.find_elements(
                    By.CSS_SELECTOR, "a[href*='/photo/']"
                )
                if(len(images) > 0):
                    url = images[0].get_attribute("href")
                    return Finder.__get_post_id(url)
                else:
                    return None
        except NoSuchElementException:
            sources = None
            pass
        except Exception as ex:
            logger.exception("Error at find_image_url method : {}".format(ex))
            sources = None

        return sources

    @staticmethod
    def __get_post_id(url):
        if '/events' in url:
            match = re.search(r"/events/(\d+)/", url)
            return match.group(1) if match else None
        if '/photo' in url:
            parsed_url = urlparse(url)
            # Get the query parameters as a dictionary
            query_params = parse_qs(parsed_url.query)
            # Get the value of the 'fbid' query parameter
            post_id = query_params.get('set', [None])[0]
            if post_id:
                post_id = post_id.split('.')[1]
            else:
                post_id = query_params.get('fbid', [None])[0]

            return post_id

        return None



    @staticmethod
    def __find_all_image_url(post, layout, driver):
        """finds all image of the facebook post using selenium's webdriver's method"""
        post_id = None
        try:
            if layout == "old":
                # find all img tag that looks like <img class="scaledImageFitWidth img" src=""> div > img[referrerpolicy]
                images = post.find_elements(
                    By.CSS_SELECTOR, "img.scaledImageFitWidth.img"
                )
                # extract src attribute from all the img tag,store it in list
            elif layout == "new":
                images = post.find_elements(
                    By.CSS_SELECTOR, "div > img[referrerpolicy]"
                )

                # will open the fb carousel and get all the images
                driver.set_window_size(1920, 1200)

                photo_viewer_xpath = '//div[@aria-label="Photo Viewer"]'

                # will try to close the carousel if it's open TODO be sure this does work
                try:
                    carousel = driver.find_element(By.XPATH, photo_viewer_xpath)
                    carousel_close_button = carousel.find_element(By.XPATH, '//div[@aria-label="Close"]')
                    carousel_close_button = carousel_close_button.find_element(By.XPATH, './ancestor::div[@role="banner"]/*[1]')
                    ActionChains(driver).move_to_element_with_offset(carousel_close_button, 0, 0).click().perform()
                    time.sleep(3)
                except Exception as exception:
                    logger.debug("carousel open not found")
                    logger.debug(exception)

                try:
                    parent_element = images[-1].find_element(By.XPATH,
                                                               './ancestor::a[contains(@href, "/photo")]')
                    last_image_count = parent_element.find_element(By.XPATH,
                                                               "..//div[contains(text(), '+')]")
                    max_images_count = len(images) + int(last_image_count.text.strip("+"))
                    logger.debug(f"image count is {max_images_count}")
                except Exception as exce:
                    max_images_count = len(images)
                    logger.debug(exce)
                first_url_element = images[0].find_element_by_xpath('./ancestor::a')

                if '/photo' not in first_url_element.get_attribute('href'):
                    # the post has no photos, could be an event
                    logger.debug("post doesn't have extra images")
                    return {
                        'post_id': Finder.__get_post_id(first_url_element.get_attribute('href')),
                        'images': [image.get_attribute('src') for image in images],
                        'error': f"post doesn't have extra images : {first_url_element.get_attribute('href')}"
                    }

                try:
                    # wait for a second to have the photo viewer render
                    WebDriverWait(driver, 20).until(EC.visibility_of(first_url_element));
                    driver.execute_script("arguments[0].scrollIntoView();", first_url_element)
                    ActionChains(driver).move_to_element_with_offset(first_url_element, 0, 0).click().perform()
                except Exception as error:
                    logger.debug("couldn't get the carousel to work")
                    logger.debug(first_url_element.get_attribute('href'))
                    logger.debug(traceback.format_exc())
                    return {
                        'images': [image.get_attribute('src') for image in images],
                        'post_id': Finder.__get_post_id(first_url_element.get_attribute('href')),
                        'error': traceback.format_exc()
                    }

                image_carousel_wrapper = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Photo Viewer"]')))
                next_button = image_carousel_wrapper.find_element(
                    By.XPATH, '//div[@data-name="media-viewer-nav-container"]//div[@data-visualcompletion]'
                )

                if image_carousel_wrapper:
                    if post_id is None:
                        post_id = Finder.__get_post_id(driver.current_url)

                def is_image_loaded(driver, img_element):
                    return driver.execute_script(
                        "return arguments[0].complete && typeof arguments[0].naturalWidth != 'undefined' && arguments[0].naturalWidth > 0",
                        img_element)
                image_src = []

                while (next_button is not None) & (len(image_src) < max_images_count):
                    try:
                        logger.debug("waiting for the image to render")
                        time.sleep(2)
                        try:
                            image = image_carousel_wrapper.find_element(
                                By.XPATH, '//img[@data-visualcompletion]',
                            )
                        except:
                            time.sleep(10)
                            image = image_carousel_wrapper.find_element(
                                By.XPATH, '//img[@data-visualcompletion]',
                            )

                        if image.get_attribute('src') in image_src:
                            next_button = None
                            break
                        WebDriverWait(driver, 30).until(lambda driver: is_image_loaded(driver, image))
                        images.append(image)
                        image_src.append(image.get_attribute('src'))
                        logger.debug(f"image url : {image.get_attribute('src')}")
                        Utilities._Utilities__close_force_login_popup(driver)
                        carousel_buttons = image_carousel_wrapper.find_elements(
                            By.XPATH, '//div[@data-name="media-viewer-nav-container"]//div[@data-visualcompletion]'
                        )
                        if (len(carousel_buttons) > 1):
                            next_button = carousel_buttons[1]
                            ActionChains(driver).move_to_element(next_button).click().perform()
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.XPATH, '//img[@data-visualcompletion]')))
                        else:
                            next_button = None
                    except Exception as exp:
                        logger.debug(exp)
                        return {
                            'images': [image.get_attribute("src") for image in images] if len(images) > 0 else [],
                            'post_id': post_id
                        }
                # closing the photo carousel to force next posts to render
                carousel_closing_button = image_carousel_wrapper.find_element(By.XPATH, '//i[@data-visualcompletion="css-img"]')
                ActionChains(driver).move_to_element(carousel_closing_button).click().perform()
                return {
                    'images': image_src,
                    'post_id': post_id
                }


        except NoSuchElementException:
            sources = []
            pass
        except Exception as ex:
            logger.exception("Error at find_image_url method : {}".format(ex))
            sources = []

        return {
            'images': sources,
            'post_id': post_id
        }

    @staticmethod
    def __find_all_posts(driver, layout, isGroup):
        """finds all posts of the facebook page using selenium's webdriver's method"""
        try:
            # find all posts that looks like <div class="userContentWrapper"> </div>
            if layout == "old":
                all_posts = driver.find_elements(
                    By.CSS_SELECTOR, "div.userContentWrapper"
                )
            elif layout == "new":
                # all_posts = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div")
                # different query selectors depending on if we are scraping a FB page or group
                # old selector div[role="article"]
                all_posts = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div" if isGroup else 'div[data-virtualized]')
            return all_posts
        except NoSuchElementException:
            logger.error("Cannot find any posts! Exiting!")
            # if this fails to find posts that means, code cannot move forward, as no post is found
            Utilities.__close_driver(driver)
            sys.exit(1)
        except Exception as ex:
            logger.exception("Error at find_all_posts method : {}".format(ex))
            Utilities.__close_driver(driver)
            sys.exit(1)

    @staticmethod
    def __find_name(driverOrPost, layout):
        """finds name of the facebook page or post using selenium's webdriver's method"""
        # Attempt to print the outer HTML of the driverOrPost for debugging

        try:
            if layout == "old":
                name = driverOrPost.find_element(By.CSS_SELECTOR, "a._64-f")
            elif layout == "new":
                name = driverOrPost.find_element(By.TAG_NAME, "strong")
            url = None
            if name is not None:
                try:
                    url_elem = name.find_element(By.XPATH, "./ancestor::a")
                    url = url_elem.get_attribute('href')
                except NoSuchElementException:
                    url_elem = name.find_element(By.XPATH, ".//a")
                    url = url_elem.get_attribute('href')
            return {
                'name' : name.get_attribute(
                    "textContent"
                ),
                'url': url
            }
        except Exception as ex:
            logger.exception("Error at __find_name method : {}".format(ex))

    @staticmethod
    def __detect_ui(driver):
        try:
            driver.find_element(By.ID, "pagelet_bluebar")
            return "old"
        except NoSuchElementException:
            return "new"
        except Exception as ex:
            logger.exception("Error art __detect_ui: {}".format(ex))
            Utilities.__close_driver(driver)
            sys.exit(1)

    @staticmethod
    def __find_reaction(layout, reactions_all):
        try:
            if layout == "old":
                return reactions_all.find_elements(By.TAG_NAME, "a")
            elif layout == "new":
                return reactions_all.find_elements(By.TAG_NAME, "div")

        except Exception as ex:
            logger.exception("Error at find_reaction : {}".format(ex))
            return ""

    @staticmethod
    def __accept_cookies(driver):
        try:
            button = driver.find_elements(
                By.CSS_SELECTOR, '[aria-label="Allow essential and optional cookies"]'
            )
            button[-1].click()
        except (NoSuchElementException, IndexError):
            pass
        except Exception as ex:
            logger.exception("Error at accept_cookies: {}".format(ex))
            sys.exit(1)

    @staticmethod
    def __login(driver, username, password):
        try:

            wait = WebDriverWait(driver, 4)  # considering that the elements might load a bit slow

            # NOTE this closes the login modal pop-up if you choose to not login above
            try:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Close"]')))
                element.click()  # Click the element
            except Exception as ex:
                logger.debug(f"no pop-up")

            time.sleep(1)
            #target username
            username_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']")))
            password_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']")))

            #enter username and password
            username_element.clear()
            username_element.send_keys(str(username))
            password_element.clear()
            password_element.send_keys(str(password))

            #target the login button and click it
            try:
                # Try to click the first button of type 'submit'
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
            except TimeoutException:
                # If the button of type 'submit' is not found within 2 seconds, click the first 'button' found
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button"))).click()
        except (NoSuchElementException, IndexError):
            pass
        except Exception as ex:
            logger.exception("Error at login: {}".format(ex))
            # sys.exit(1)
