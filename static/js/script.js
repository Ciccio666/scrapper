/**
 * Web Scraper Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const scrapeForm = document.getElementById('scrapeForm');
    const scrapeButton = document.getElementById('scrapeButton');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsContainer = document.getElementById('resultsContainer');
    const errorContainer = document.getElementById('errorContainer');
    const copyResultsBtn = document.getElementById('copyResultsBtn');
    
    // Form Elements
    const urlInput = document.getElementById('url');
    const userAgentSelect = document.getElementById('userAgent');
    const waitTimeInput = document.getElementById('waitTime');
    const headlessModeCheckbox = document.getElementById('headlessMode');
    const disableImagesCheckbox = document.getElementById('disableImages');
    
    // Crawling Options
    const enableCrawlingCheckbox = document.getElementById('enableCrawling');
    const crawlOptionsContainer = document.querySelector('.crawl-options');
    const maxDepthInput = document.getElementById('maxDepth');
    const maxPagesInput = document.getElementById('maxPages');
    const restrictToDomainCheckbox = document.getElementById('restrictToDomain');
    const followExternalLinksCheckbox = document.getElementById('followExternalLinks');
    const ignoreQueryStringsCheckbox = document.getElementById('ignoreQueryStrings');
    
    // Toggle crawl options visibility
    enableCrawlingCheckbox.addEventListener('change', function() {
        if (this.checked) {
            crawlOptionsContainer.style.display = 'block';
        } else {
            crawlOptionsContainer.style.display = 'none';
        }
    });
    
    // API endpoint
    const SCRAPE_API_ENDPOINT = '/api/scrape';
    
    /**
     * Handle form submission
     */
    scrapeForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Hide previous results or errors
        resultsContainer.classList.add('d-none');
        errorContainer.classList.add('d-none');
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        
        // Disable submit button
        scrapeButton.disabled = true;
        scrapeButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scraping...';
        
        // Prepare request data
        const requestData = {
            url: urlInput.value.trim(),
            user_agent: userAgentSelect.value,
            selenium_options: {
                headless: headlessModeCheckbox.checked,
                disable_images: disableImagesCheckbox.checked,
                wait_time: parseFloat(waitTimeInput.value) || 2.0
            }
        };
        
        // Add crawling options if enabled
        if (enableCrawlingCheckbox.checked) {
            requestData.crawl_options = {
                enabled: true,
                max_depth: parseInt(maxDepthInput.value) || 1,
                max_pages: parseInt(maxPagesInput.value) || 10,
                follow_external_links: followExternalLinksCheckbox.checked,
                restrict_to_domain: restrictToDomainCheckbox.checked,
                ignore_query_strings: ignoreQueryStringsCheckbox.checked
            };
        }
        
        // Make API request
        fetch(SCRAPE_API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            if (data.status === 'success') {
                // Show results
                displayResults(data);
                resultsContainer.classList.remove('d-none');
            } else {
                // Show error
                document.getElementById('errorMessage').textContent = data.error || 'Failed to scrape the website';
                document.getElementById('errorDetails').textContent = data.details || '';
                errorContainer.classList.remove('d-none');
            }
        })
        .catch(error => {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            // Show error
            document.getElementById('errorMessage').textContent = 'Network or server error';
            document.getElementById('errorDetails').textContent = error.message || '';
            errorContainer.classList.remove('d-none');
        })
        .finally(() => {
            // Reset button state
            scrapeButton.disabled = false;
            scrapeButton.innerHTML = '<i class="bi bi-search me-2"></i>Scrape Website';
        });
    });
    
    /**
     * Display scraped results in the UI
     */
    function displayResults(data) {
        const scrapedData = data.data;
        
        // Overview tab
        document.getElementById('resultTitle').textContent = scrapedData.title || 'No title found';
        document.getElementById('resultDescription').textContent = scrapedData.description || 'No description found';
        
        // URL information
        const urlElement = document.getElementById('resultUrl');
        const urlLink = urlElement.querySelector('a') || document.createElement('a');
        urlLink.href = scrapedData.url.final;
        urlLink.textContent = scrapedData.url.final;
        urlLink.target = '_blank';
        if (urlElement.querySelector('a') === null) {
            urlElement.innerHTML = '';
            urlElement.appendChild(urlLink);
        }
        
        // Content stats
        document.getElementById('contentLength').textContent = scrapedData.metadata.content_length.toLocaleString();
        document.getElementById('linksCount').textContent = scrapedData.metadata.elements.links.toLocaleString();
        document.getElementById('imagesCount').textContent = scrapedData.metadata.elements.images.toLocaleString();
        
        // Scraping stats
        document.getElementById('userAgentUsed').textContent = scrapedData.metadata.user_agent;
        document.getElementById('scrapeTime').textContent = `${scrapedData.metadata.scrape_time_seconds}s`;
        
        const redirectStatus = document.getElementById('redirectStatus');
        if (scrapedData.url.was_redirected) {
            redirectStatus.textContent = 'Yes';
            redirectStatus.classList.add('bg-info');
            redirectStatus.classList.remove('bg-secondary');
        } else {
            redirectStatus.textContent = 'No';
            redirectStatus.classList.add('bg-secondary');
            redirectStatus.classList.remove('bg-info');
        }
        
        // Content tab
        document.getElementById('contentArea').value = scrapedData.content;
        
        // Metadata tab
        const metadataTable = document.getElementById('metadataTable');
        metadataTable.innerHTML = '';
        
        // Function to create table rows
        function addMetadataRow(property, value) {
            const row = document.createElement('tr');
            
            const propertyCell = document.createElement('td');
            propertyCell.textContent = property;
            
            const valueCell = document.createElement('td');
            if (typeof value === 'boolean') {
                const badge = document.createElement('span');
                badge.classList.add('badge', 'rounded-pill');
                
                if (value) {
                    badge.classList.add('bg-success');
                    badge.textContent = 'Yes';
                } else {
                    badge.classList.add('bg-secondary');
                    badge.textContent = 'No';
                }
                
                valueCell.appendChild(badge);
            } else {
                valueCell.textContent = value;
            }
            
            row.appendChild(propertyCell);
            row.appendChild(valueCell);
            metadataTable.appendChild(row);
        }
        
        // Add metadata rows
        addMetadataRow('Original URL', scrapedData.url.original);
        addMetadataRow('Final URL', scrapedData.url.final);
        addMetadataRow('Was Redirected', scrapedData.url.was_redirected);
        addMetadataRow('Content Length', scrapedData.metadata.content_length);
        addMetadataRow('Scrape Time', `${scrapedData.metadata.scrape_time_seconds} seconds`);
        addMetadataRow('Has Title', scrapedData.metadata.has_title);
        addMetadataRow('Has Description', scrapedData.metadata.has_description);
        addMetadataRow('User Agent', scrapedData.metadata.user_agent);
        addMetadataRow('Is Dynamic', scrapedData.metadata.is_dynamic);
        
        // Element counts
        addMetadataRow('Links Count', scrapedData.metadata.elements.links);
        addMetadataRow('Images Count', scrapedData.metadata.elements.images);
        addMetadataRow('Forms Count', scrapedData.metadata.elements.forms);
        addMetadataRow('Scripts Count', scrapedData.metadata.elements.scripts);
        addMetadataRow('Total Elements', scrapedData.metadata.elements.total);
        
        // Raw JSON tab
        document.getElementById('rawJsonArea').value = JSON.stringify(data, null, 2);
    }
    
    /**
     * Copy results to clipboard
     */
    copyResultsBtn.addEventListener('click', function() {
        const rawJsonArea = document.getElementById('rawJsonArea');
        
        // Select and copy text
        rawJsonArea.select();
        document.execCommand('copy');
        
        // Change button text temporarily
        const originalText = copyResultsBtn.innerHTML;
        copyResultsBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Copied!';
        
        // Reset button text after 2 seconds
        setTimeout(() => {
            copyResultsBtn.innerHTML = originalText;
        }, 2000);
    });
});