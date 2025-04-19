/**
 * Web Scraper Settings Page JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI
    getSettings();
    
    // Set up event listeners
    document.getElementById('refreshButton').addEventListener('click', getSettings);
    document.getElementById('saveButton').addEventListener('click', saveSettings);
    
    // Add example button listener
    document.getElementById('loadExampleButton').addEventListener('click', loadExample);
    
    // Add form listeners
    setupFormListeners();
});

/**
 * Get current settings from the API
 */
function getSettings() {
    fetch('/api/settings_yaml')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error fetching settings');
            }
            return response.text();
        })
        .then(yamlText => {
            document.getElementById('yamlEditor').value = yamlText;
            updateResponseStatus('Settings loaded successfully', 'success');
        })
        .catch(error => {
            console.error('Error:', error);
            updateResponseStatus(`Error: ${error.message}`, 'danger');
        });
}

/**
 * Save settings to the API
 */
function saveSettings() {
    const yamlText = document.getElementById('yamlEditor').value;
    
    fetch('/api/settings_yaml', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/yaml',
        },
        body: yamlText
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || 'Error saving settings');
            });
        }
        return response.json();
    })
    .then(data => {
        updateResponseStatus('Settings saved successfully', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        updateResponseStatus(`Error: ${error.message}`, 'danger');
    });
}

/**
 * Update the response status box
 */
function updateResponseStatus(message, type) {
    const statusEl = document.getElementById('responseStatus');
    statusEl.innerHTML = message;
    statusEl.className = `alert alert-${type}`;
}

/**
 * Load an example configuration
 */
function loadExample() {
    const exampleYaml = `# Time and delay settings
page_load_timeout: 30
dynamic_content_wait: 2.0
chatgpt_min_wait: 5.0
chatgpt_max_wait: 8.0

# Crawling depth settings
max_depth: 2
max_pages_per_domain: 20

# Domain restriction settings
restrict_to_domains: 
  - example.com
  - news.example.com
follow_external_links: false

# Content filtering settings
ignore_query_strings: true
exclude_url_patterns:
  - ".*\\.pdf$"
  - "/login"
  - "/logout"
  - "/account"`;
  
    document.getElementById('yamlEditor').value = exampleYaml;
    updateResponseStatus('Example configuration loaded. Click "Save Changes" to apply.', 'info');
}

/**
 * Set up form listeners for the detailed settings form
 */
function setupFormListeners() {
    // Domain restriction form
    const domainForm = document.getElementById('domainForm');
    if (domainForm) {
        domainForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const domainInput = document.getElementById('newDomain');
            const domain = domainInput.value.trim();
            
            if (domain) {
                addDomainToList(domain);
                domainInput.value = '';
            }
        });
    }
    
    // URL pattern form
    const patternForm = document.getElementById('patternForm');
    if (patternForm) {
        patternForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const patternInput = document.getElementById('newPattern');
            const pattern = patternInput.value.trim();
            
            if (pattern) {
                addPatternToList(pattern);
                patternInput.value = '';
            }
        });
    }
}

/**
 * Add a domain to the restricted domains list
 */
function addDomainToList(domain) {
    const domainList = document.getElementById('restrictedDomains');
    
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    li.innerHTML = `
        ${domain}
        <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.remove();">
            <i class="bi bi-trash"></i>
        </button>
    `;
    
    domainList.appendChild(li);
}

/**
 * Add a pattern to the excluded patterns list
 */
function addPatternToList(pattern) {
    const patternList = document.getElementById('excludedPatterns');
    
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    li.innerHTML = `
        ${pattern}
        <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.remove();">
            <i class="bi bi-trash"></i>
        </button>
    `;
    
    patternList.appendChild(li);
}

/**
 * Update YAML from form values (for interactive editor)
 */
function updateYamlFromForm() {
    // This would collect all form values and update the YAML text
    // Placeholder for future enhancement
}