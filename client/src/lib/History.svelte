
<script>
    let history = "History";
    let dummyList = ["How many invoices do I have?", "Who are my biggest competitors?", "What does my insurance protect me against?", "When is my next payment due?"];
  </script>


<div class="wrapper">
    <h3>{history}</h3>
  
    <div class="list-container">
      {#each dummyList as item}
        <div class="history-item">{item}</div>
      {/each}
    </div>
  </div>
