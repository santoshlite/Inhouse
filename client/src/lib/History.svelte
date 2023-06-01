
<script>
    let history = "History";
    let dummyList = ["How many invoices do I have?", "Who are my biggest competitors?", "What does my insurance protect me against?", "When is my next payment due?"];
  </script>


<div class="wrapper">
  <div class="title">{history}</div>
    <div class="list-container">
      {#each dummyList as item}
        <div class="history-item">📄 &nbsp; {item}</div>
      {/each}
    </div>
  </div>
