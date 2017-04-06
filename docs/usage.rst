.. _tutorial:

Tutorial
========
Once you have Aniping set up as in the :ref:`quick-start`, or using a more advanced setup, using it is pretty simple.

Before you do anything else, open up aniping in your web browser. If you followed the :ref:`quick-start` exactly, you should be able to open ``http://localhost`` on the same machine as your running container. Otherwise, you'll need to get your running container's IP address, or assign it a hostname. Once you are on the aniping home, you'll see that it is trying to populate its database. This can take 5 to 10 minutes, so just sit back and let it do it's thing.

It will refresh when it has data to show, but it might not be completely done at that point. After 10 minutes or so, refresh the page and you should see all of this season's shows.

Logging In and Out
------------------
At the top right, next to the search box, is a simple log in and out form. This may already say "log out" if you have authentication disabled on sonarr. If you do not and it says "log in", simply log in with the same username and password you use for sonarr. If you were successful, it will replace the link with a "log out" button. When you press it, it will instantly log you out.

Searching for shows
-------------------
You can search for shows currently airing by using the search box. The search box is not very advanced, and cannot correct typos or misspellings, but it does search titles, studios, descriptions, and genres. It will not search sonarr, it will only search what it has in it's database.

Highlighting shows
------------------
On desktop, when you are logged in, hover over a card and click the "star" button. The background of that card will turn yellow. Click it again to unhighlight it. This can be used to mark shows you want to watch, but you are waiting for whatever reason to start it.

On mobile, the star will always be visible.

Selecting a show
----------------
To select a show, hover over a card and click the "+" button. This should take you to a page with a more detailed description of the show, this time coming directly from sonarr's search. If sonarr cannot find the show, you will be redirected back to the home page.

Once on the show description page, simply select which release group you would like working on the show, and click "Add show". This will automatically create a tag with a restriction in sonarr if necessary, and add the show to sonarr's list.

On mobile, the "+" will always be visible.

Editing a show
--------------
Any show in the "watching" category will have an edit button instead of a "+" button when rolled over. Click this button and you will be given the same interface as the show selection button. Make the appropriate change and click "Edit show", and the show will be updated.

On mobile, the "edit" button will always be visible.

Deleting a show
---------------
If you no longer wish to have sonarr tracking a show, you can delete it by clicking the "x" button. It will not delete anything sonarr has already gathered.