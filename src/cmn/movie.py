import pandas as pd
from tqdm import tqdm
import traceback
import pickle
from time import time
import os
from collections import Counter
from os import listdir, write
from csv import DictReader
from csv import reader
from cmn.team import Team
from cmn.member import Member
from cmn.castncrew import CastnCrew


class Movie(Team):

    def __init__(self, id, members, p_title, o_title, release, end, runtime, genres, members_details):
        super().__init__(id, members, None, release)
        self.p_title = p_title
        self.o_title = o_title
        self.release = release
        self.end = end
        self.runtime = runtime
        self.genres = genres
        self.members_details = members_details
        self.skills = self.set_skills()

        for i, member in enumerate(self.members):
            member.teams.add(self.id)
            member.skills.union(set(self.skills))
            member.role.add(self.members_details[i])

    def set_skills(self):
        return set(self.genres.split(','))

    @staticmethod
    def read_data(datapath, output, index, filter, settings):
        st = time()
        try:
            return super(Movie, Movie).load_data(output, index)
        except (FileNotFoundError, EOFError) as e:
            print("Pickles not found! Reading raw data ...")
            # in imdb, title.* represent movies and name.* represent crew members

            title_basics = pd.read_csv(datapath, sep='\t', header=0, na_values='\\N',dtype={"startYear": "Int64", "endYear": "Int64"}, low_memory=False).sort_values(by=['tconst'])  # title.basics.tsv
            title_basics = title_basics[title_basics['titleType'].isin(['movie', ''])]
            title_principals = pd.read_csv(datapath.replace('title.basics', 'title.principals'), sep='\t', header=0,na_values='\\N',dtype={"birthYear": "Int64", "deathYear": "Int64"},low_memory=False)  # movie-crew association for top-10 cast
            name_basics = pd.read_csv(datapath.replace('title.basics', 'name.basics'), sep='\t', header=0,na_values='\\N',low_memory=False)  # name.basics.tsv

            movies_crewids = pd.merge(title_basics, title_principals, on='tconst', how='inner', copy=False)
            movies_crewids_crew = pd.merge(movies_crewids, name_basics, on='nconst', how='inner', copy=False)

            movies_crewids_crew.dropna(subset=['genres'], inplace=True)
            movies_crewids_crew = movies_crewids_crew.append(pd.Series(), ignore_index=True)

            teams = {}; candidates = {}; n_row = 0
            current = None
            #for index, movie_crew in tqdm(movies_crewids_crew.iterrows(), total=movies_crewids_crew.shape[0]):#54%|█████▍    | 2036802/3776643 [04:20<03:37, 7989.97it/s]
            # for index in tqdm(range(0, movies_crewids_crew.shape[0], 1)):#50%|█████     | 1888948/3776643 [06:06<06:12, 5074.40it/s]
            #     movie_crew = movies_crewids_crew.loc[index]
            for movie_crew in tqdm(movies_crewids_crew.itertuples(), total=movies_crewids_crew.shape[0]):#100%|███████████|3776642it [01:05, 57568.62it/s]
                try:
                    if pd.isnull(new := movie_crew.tconst): break
                    if current != new:
                        team = Movie(movie_crew.tconst.replace('tt', ''),
                                     [],
                                     movie_crew.primaryTitle,
                                     movie_crew.originalTitle,
                                     movie_crew.startYear,
                                     movie_crew.endYear,
                                     movie_crew.runtimeMinutes,
                                     movie_crew.genres,
                                     [])
                        current = new
                        teams[team.id] = team

                    member_id = movie_crew.nconst.replace('nm', '')
                    member_name = movie_crew.primaryName.replace(" ", "_")
                    if (idname := f'{member_id}_{member_name}') not in candidates:
                        candidates[idname] = CastnCrew(movie_crew.nconst.replace('nm', ''),
                                                       movie_crew.primaryName.replace(' ', '_'),
                                                       movie_crew.birthYear,
                                                       movie_crew.deathYear,
                                                       movie_crew.primaryProfession,
                                                       movie_crew.knownForTitles,
                                                       None)
                    team.members.append(candidates[idname])
                    team.members_details.append((movie_crew.category, movie_crew.job, movie_crew.characters))
                except Exception as e:
                    raise e
            return super(Movie, Movie).read_data(teams, output, filter, settings)