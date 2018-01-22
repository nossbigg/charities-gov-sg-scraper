## charities.gov.sg scraper: methodology

1. go to source website
2. click on 'Search' button
3. scrape charity organization information using selenium + beautifulsoup
4. go to next page and do scrape until no more pages left
5. save scrape information into csv/json

## cafa scraper: methodology

1. make get request to api
2. get number of charities
3. calculate page indexes
4. scrape paginated api response 
5. save scrape information into csv/json

## dependencies

1. [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/) 

code tested with ChromeDriver 2.35

place executable in ./selenium_drivers folder

2. python libraries
- selenium
- beautifulsoup
- pandas
