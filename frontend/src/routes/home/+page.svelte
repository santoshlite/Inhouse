<script>
// @ts-nocheck
import { onMount } from 'svelte';
import History from '/src/History.svelte';
import '/src/routes/styles.css';

let responseValue = "Ready to take your questions!";
let inputValue = "";
let indexedInfo = "";
let question = "";
let blocksList = [];
let historylist = [];
let showInputBox = false;
let isSearching = false; // To prevent multiple searches
let urlGoogle, fileInput;
let base = import.meta.env.VITE_API_DOMAIN;

async function getHistoryList() {
    const response = await fetch(base + `home/get_history_list/`);
    const data = await response.json();

    if (response.ok) {
        historylist = data.queries;
    } else {
        historylist = ["Could not load history"];
    }
}

async function getUploadedItems() {
    const response = await fetch(base + `home/get_uploaded_count/`);
    const data = await response.text();
    return data;
}

async function fetchData() {
    const count = await getUploadedItems();
    if (count === "0") {
        indexedInfo = "Upload files to get started!";
        return;
    } else if (count === "1") {
        indexedInfo = count + " file indexed";
        return;
    }
    indexedInfo = count + " files indexed.";
}

async function search() {
    responseValue = "";
    if (inputValue === "") {
        responseValue = "No text :(";
        return;
    } else if (indexedInfo === "Upload files to get started!") {
        responseValue = "Upload files first";
        return;
    }
    isSearching = true;
    question = "";
    responseValue = "Waiting for the LLM...";
    blocksList = [];

    const response = await fetch(base + `home/search/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/x-ndjson'
        },
        body: JSON.stringify({
            value: inputValue
        })
    });

    const reader = response.body.getReader();

    const chunks = [];
    responseValue = "Waiting for the LLM...";
    blocksList = [];

    while (true) {
        const {
            done,
            value
        } = await reader.read();

        if (done) {
            // End of streaming
            break;
        }

        const decoder = new TextDecoder();
        const decodedValue = decoder.decode(value);
        const parsed = JSON.parse(decodedValue);

        if (parsed.response) {
            // Perform actions when the "response" field exists
            question = "Q: " + inputValue;
            responseValue = parsed.response.result;
            blocksList = parsed.response.blocks;
            break;
        }
        chunks.push(parsed.status);
        responseValue = chunks[chunks.length - 1];
        await getHistoryList();
    }
}

async function askUrl() {
    showInputBox = true;
}

async function uploadGoogle() {

    showInputBox = false;

    if (urlGoogle === "") {
        indexedInfo = "URL is empty :(";
        return;
    }

    indexedInfo = "Loading your Google Drive folder...";

    const response = await fetch(base + `home/upload_google_file/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: urlGoogle
        })
    });

    const data = await response.json();
    const count = await getUploadedItems();
    indexedInfo = data.Message + " " + count + " indexed.";

    await getHistoryList();
}

async function uploadFile() {
    indexedInfo = "Uploading...";

    const formData = new FormData();

    const allowedFileTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/webp'];
    let unsupportedFiles = [];

    for (let i = 0; i < fileInput.files.length; i++) {
        if (allowedFileTypes.includes(fileInput.files[i].type)) {
            unsupportedFiles.push(fileInput.files[i].name);
            continue;
        }
        formData.append('files[]', fileInput.files[i]);
    }
    const response = await fetch(base + `home/upload_file/`, {
        method: 'POST',
        body: formData
    });

    if (unsupportedFiles.length > 0) {
        const warningMessage = `Could not upload the following files. Image type files are not allowed: ${unsupportedFiles.join(', ')}`;
        alert(warningMessage);
    }

    const data = await response.json();
    fetchData();
}

async function fetchResponse(query) {
    const response = await fetch(base + `home/get_response_from_query/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            value: query
        })
    });

    if (response.ok) {
        const data = await response.json();
        responseValue = data.result;
        question = "Q: " + data.query;
        blocksList = data.blocks;
    } else {
        responseValue = "Error fetching response.";
    }
}

function handleKeyDown(event) {
    if (event.key === "Enter" && !isSearching) {
        search();
    }
}

function handleFileChange(event) {
    fileInput = event.target;
    uploadFile();
}

async function syncGoogle() {
    indexedInfo = "Syncing with Google Drive...";
    const response = await fetch(base + `home/sync_google/`);
    const data = await response.json();
    if (data.Message === "X") {
        await fetchData();
    } else {
        const count = await getUploadedItems();
        indexedInfo = data.Message + ". " + count + " indexed.";
    }
    return data;
}

onMount(async () => {
    await fetchData();
    await getHistoryList();
    await syncGoogle();
});
</script>

<svelte:head>
    <title>Inhouse | Home</title>
    <meta name="description" content="User's homepage" />
    </svelte:head>

    <div class="row">
        <History historyList={historylist} fetchResponse={fetchResponse}/>
            </div>

            <div class="row-bar">
                <div class="top-bar">
                    <h1>inhouse 🏠</h1>
                    <div class="search-container">
                        <div class="input-container">
                            <input placeholder="Ask a question." class="searchbar" type="text" bind:value={inputValue} on:keydown={handleKeyDown}/>
                            <button class="submit-button" on:click={search}>🔍</button>
                        </div>

                    </div>
                    <div class="uploads">
                        <div class="upload-button-container">
                            <label for="fileInput" class="upload-button">
                                📥  &thinsp; Upload
                                <input id="fileInput" type="file" style="display:none" on:change={handleFileChange} multiple />
                            </label>
                        </div>

                        <div class="gdrive-button-container">
                            <label class="gdrive-button">
                                <img src="https://upload.wikimedia.org/wikipedia/commons/1/12/Google_Drive_icon_%282020%29.svg" alt="google drive icon"/> &thinsp; Sync Drive
                                <input type="text" style="display:none" on:click={askUrl}/>
                            </label>
                        </div>
                    </div>

                    {#if showInputBox}
                    <div>
                        <input type="text" placeholder="Share link to a folder..." bind:value={urlGoogle}/>
                        <button on:click={uploadGoogle}>Sync</button>
                    </div>
                    {/if}
                    <p class="custom-i">{indexedInfo}</p>
                </div>

                <div class="wrapper-response">
                    <p class="response"><b class="query">{question}</b>{@html responseValue}</p>
                    {#each blocksList as block}
                    <div class="wrapper-block">
                        <div class="title-tag">
                            {@html block.tag}
                            <p class="docname">{block.document_name}</p>
                        </div>
                        <p>{block.block}</p>

                    </div>
                    {/each}
                </div>

            </div>
