from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread, Lock
from urllib import parse
import time

class Scraper:
    
    def __init__(self, num_threads = 1, show_ui = True) -> None:
        self.__num_threads = num_threads
        self.__show_ui = show_ui
        self.__drivers = []

        self._initialize_scraper()

    def _initialize_scraper(self):
        pool = []
        for i in range(self.__num_threads):
            thread = Thread(target = self._create_driver)
            pool.append(thread)
            thread.start()
        
        for thread in pool:
            thread.join()
            
    def _create_threads(self):
        for i in range(self.__num_threads):
            thread = Thread(target = self._get_images, args = (self.__drivers[i],))
            self.__threads_pool.append(thread)
            thread.start()

    def _destroy_threads(self):
        for thread in self.__threads_pool:
            thread.join()

    def _create_driver(self):
        self.__options = webdriver.ChromeOptions()
        self.__options.add_argument("incognito")
        if not self.__show_ui:
            self.__options.add_argument("headless")
            self.__options.add_argument('--no-sandbox')
            self.__options.add_argument("--window-size=1920,1080")
        else:
            self.__options.add_argument('--start-maximized')
        self.__options.add_argument('--disable-dev-shm-usage')
        self.__options.add_argument('--start-maximized')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.__options)
        browser_version = 'Failed to detect version'
        chromedriver_version = 'Failed to detect version'
        major_version_different = False

        if 'browserVersion' in driver.capabilities:
            browser_version = str(driver.capabilities['browserVersion'])

        if 'chrome' in driver.capabilities:
            if 'chromedriverVersion' in driver.capabilities['chrome']:
                chromedriver_version = str(driver.capabilities['chrome']['chromedriverVersion']).split(' ')[0]

        if browser_version.split('.')[0] != chromedriver_version.split('.')[0]:
            major_version_different = True

        print('_________________________________')
        print('Current web-browser version:\t{}'.format(browser_version))
        print('Current chrome-driver version:\t{}'.format(chromedriver_version))
        if major_version_different:
            print('warning: Version different')
            print(
                'Download correct version at "http://chromedriver.chromium.org/downloads" and place in "./chromedriver"')
        print('_________________________________')
        driver.get("https://www.google.com/imghp?hl=en")
        self.__drivers.append(driver)

    def _load_thumbnails(self, driver):
        def get_thumbnails():
            try:
                print("\nFetching image thumbnails...")
                thumbnails = driver.find_elements(By.XPATH, "//div[@class='eA0Zlc WghbWd FnEtTd mkpRId m3LIae RLdvSe qyKxnc ivg-i PZPZlf GMCzAd']")
                # thumbnails = driver.find_elements(By.XPATH, "//div[@class='isv-r PNCib ViTmJb BUooTd']")
                print(f"🤖: Found {len(thumbnails)} image thumbnails!")
            except Exception as e:
                print("\n🔴🔴 Error while fetching image containers! 🔴🔴")
            return thumbnails
        thumbnails = get_thumbnails()

        while len(thumbnails) < self.__image_limit:
            print("🤖: Scrolling...")
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            thumbnails = get_thumbnails()

            try:
                end_of_page = driver.find_element(By.XPATH, """//input[@class='LZ4I']""").is_displayed()
                end_of_page2 = driver.find_element(By.XPATH, """//span[@class='XfJHbe']""").is_displayed()
                no_more_results = driver.find_element(By.XPATH, """//div[@class='OuJzKb Yu2Dnd']""").is_displayed()
                if end_of_page:
                    driver.find_element(By.XPATH, """//input[@class='LZ4I']""").click()
                    
                if end_of_page2:
                    driver.find_element(By.XPATH, """//span[@class='XfJHbe']""").click()

                if no_more_results:
                    break
            except Exception as e:
                print("\n🔴🔴 Search more button not found! 🔴🔴")

        print(f"🤖: Found a total of {len(thumbnails)} image thumbnails!") 
        driver.execute_script("window.scrollTo(0,0)")
        return thumbnails

    def _get_images(self, driver):
        # driver = webdriver.Chrome()
        driver.get(self.__url)
        thumbnails = self._load_thumbnails(driver)
        
        wait = WebDriverWait(driver, 10)
        print("\nFetching Links...")

        while len(self.__images) < self.__image_limit:   
            self.__shared_index_lock.acquire()
            index = self.__shared_index
            self.__shared_index += 1
            self.__shared_index_lock.release()
            try:
                if not index >= self.__image_limit:
                    # print(len(self.__images))
                    thumbnails[index].click()
                    # print(index)
                    wait.until(EC.visibility_of_element_located((By.XPATH, """//img[@class='sFlh5c pT0Scc iPVvYb']""")))
                    img_window = driver.find_element(By.XPATH, """//img[@class='sFlh5c pT0Scc iPVvYb']""")
                    # time.sleep(2)
                    link = img_window.get_attribute('src')
                    self.__images.add(link)
                    print(link)
                else:
                    print("✔️✔️✔️ Links Scraping complete! ✔️✔️✔️")
                    break
                                    
            except Exception as e:
                # print(thumbnails[index])
                # time.sleep(1000)
                print(" \n🔴🔴 Link not found! 🔴🔴")
                continue

    @staticmethod
    def create_url(search_query):
        parsed_query = parse.urlencode({'q': search_query})
        url = f"https://www.google.com/search?{parsed_query}&source=lnms&tbm=isch&sa=X&ved=2ahUKEwjR5qK3rcbxAhXYF3IKHYiBDf8Q_AUoAXoECAEQAw&biw=1291&bih=590"
        return url

    def scrape(self, query, count):
        self.__threads_pool = []
        self.__shared_index = 0
        self.__shared_index_lock = Lock()
        self.__images = set()

        self.__url = self.create_url(query)
        self.__image_limit = count
        start = time.time()
        self._create_threads()
        self._destroy_threads()
        end = time.time()
        print(len(self.__images))
        
        print(f"Total elapsed time for {self.__image_limit} images is: {(end - start) / 60} mins")
        return self.__images
