-- Schema for aniping

-- Main anime list table
create table airing_anime_list (
	-- id:					local ID
	id						integer primary key autoincrement not null,
	
	-- aid:		 			AnimeID, defined by anilist.co
	aid						integer not null,
	
	-- beid:				Backend ID, defined by our backend, sonarr/tvdb. Only exists when show added to backend.
	beid					integer,
	
	-- Type of show:	 	tv, ova, movie are valid right now, but others could work.
	type					text,
	
	-- Title:	 			offical title of the show according to anidb
	title					text,
	
	-- Alt_title:	 		title when translated into english preferably, alternative titles otherwise.
	alt_title				text,
	
	-- Total_episodes: 		Total number of episodes for the show.
	total_episodes			integer,
	
	-- Next_episode: 		Next episode to air, according to anilist.co
	next_episode			integer,
	
	-- Next_episode_date: 	The day the next episode is due to air.
	next_episode_date		date,
	
	-- Start_date:			The date the show starts airing.
	start_date				date,
	
	-- genre:				A comma sparated list of genres.
	genre					text,
	
	-- Studio:				The main studio producing the show.
	studio					text,
	
	-- description:			A description of the show.
	description				text,
	
	-- Link:				The link to the show on anilist
	link					text,
	
	-- image:				The relative link to the local cache of the image for the show.
	image					text,
	
	-- airing:				The airing status of the show, according to anilist.co.
	airing					text,
	
	-- season_name			This season's name: winter, spring, summer or fall.
	season_name				text,
	
    -- starred: 	        Marks if we have starred this to look it up later
    starred         	    integer not null
);

-- Cookies table
create table cookies(
	-- id:			local ID
	id				integer primary key autoincrement not null,
	
	-- cookie_id:	ID of cookie on remote system
	cookie_id		text,
	
	-- expiration:	Time to delete from DB. Should be short.
	expiration		date
);

-- Virtual table for FTS
create virtual table show_search using fts4(
	-- id:			ID of item in airing_anime_list
	id,
	--search_data:	Data to search when doing FTS
	search_data
);

-- Trigger to create items in FTS DB when created in DB
create trigger add_to_search after insert on airing_anime_list
begin
	insert into show_search (id, search_data) values (new.id, ifnull(new.title,'') || ' ' || ifnull(new.type,'') || ' ' || ifnull(new.alt_title,'') || ' ' || ifnull(new.genre,'') || ' ' || ifnull(new.studio,'') || ' ' || ifnull(new.description,'') || ' ' || ifnull(new.link,''));
end;

-- Trigger to update items in FTS DB when modified in DB
create trigger modify_search after update on airing_anime_list
begin
	update show_search set search_data=ifnull(new.title,'') || ' ' || ifnull(new.type,'') || ' ' || ifnull(new.alt_title,'') || ' ' || ifnull(new.genre,'') || ' ' || ifnull(new.studio,'') || ' ' || ifnull(new.description,'') || ' ' || ifnull(new.link,''), id=new.id where id=old.id;
end;

-- Trigger to delete items in FTS DB when deleted in DB
create trigger delete_from_search before delete on airing_anime_list
begin
	delete from show_search where id=old.id;
end;