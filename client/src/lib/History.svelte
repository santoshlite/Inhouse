
<script>
  export let historyList = [];

  function hasItems(list) {
    return list && list.length > 0;
  }
  
</script>


<div class="wrapper">
  <div class="title">History</div>

  {#if hasItems(historyList)}
    <div class="list-container">
      {#each historyList as item}
        <div class="history-item">📄 &nbsp; {item}</div>
      {/each}
    </div>
  {:else}
    <div class="empty-message">It's quiet here...</div>
  {/if}
</div>
