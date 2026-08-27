class SuggestionVoteView(discord.ui.View):
    def __init__(
        self,
        database: Database,
        suggestion_id: int,
    ) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.suggestion_id = suggestion_id

        # Make every suggestion's buttons unique.
        self.upvote.custom_id = (
            f"nexus:suggest:{suggestion_id}:up"
        )
        self.downvote.custom_id = (
            f"nexus:suggest:{suggestion_id}:down"
        )

    async def _refresh_message(
        self,
        interaction: discord.Interaction,
    ) -> None:
        suggestion = await self.database.get_suggestion(
            self.suggestion_id
        )

        if suggestion is None:
            return

        # suggestions table:
        # suggestion_id, guild_id, user_id, content,
        # status, upvotes, downvotes, timestamp
        (
            suggestion_id,
            guild_id,
            author_id,
            content,
            status,
            upvotes,
            downvotes,
            timestamp,
        ) = suggestion

        if not interaction.message:
            return

        embed = (
            interaction.message.embeds[0]
            if interaction.message.embeds
            else discord.Embed(
                title="💡 Suggestion"
            )
        )

        # Keep the existing suggestion content.
        if not embed.description:
            embed.description = content

        # Update the vote fields.
        found_up = False
        found_down = False

        for index, field in enumerate(embed.fields):
            name = field.name.lower()

            if "upvote" in name:
                embed.set_field_at(
                    index,
                    name="👍 Upvotes",
                    value=str(upvotes),
                    inline=True,
                )
                found_up = True

            elif "downvote" in name:
                embed.set_field_at(
                    index,
                    name="👎 Downvotes",
                    value=str(downvotes),
                    inline=True,
                )
                found_down = True

        if not found_up:
            embed.add_field(
                name="👍 Upvotes",
                value=str(upvotes),
                inline=True,
            )

        if not found_down:
            embed.add_field(
                name="👎 Downvotes",
                value=str(downvotes),
                inline=True,
            )

        # Keep buttons showing the current totals.
        self.upvote.label = f"Upvote • {upvotes}"
        self.downvote.label = f"Downvote • {downvotes}"

        await interaction.message.edit(
            embed=embed,
            view=self,
        )

    async def _vote(
        self,
        interaction: discord.Interaction,
        up: bool,
    ) -> None:
        user_id = interaction.user.id

        current_vote = await self.database.get_suggestion_vote(
            self.suggestion_id,
            user_id,
        )

        requested_vote = 1 if up else -1

        if current_vote == requested_vote:
            label = "upvoted" if up else "downvoted"

            return await interaction.response.send_message(
                f"You have already {label} this suggestion.",
                ephemeral=True,
            )

        success = await self.database.vote_suggestion(
            self.suggestion_id,
            user_id,
            up,
        )

        if not success:
            return await interaction.response.send_message(
                "Suggestion not found.",
                ephemeral=True,
            )

        if current_vote is None:
            message = (
                "👍 Your upvote has been recorded."
                if up
                else "👎 Your downvote has been recorded."
            )

        elif current_vote == -1 and up:
            message = (
                "Your vote has been changed "
                "from Downvote to Upvote."
            )

        else:
            message = (
                "Your vote has been changed "
                "from Upvote to Downvote."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

        try:
            await self._refresh_message(interaction)
        except (discord.NotFound, discord.HTTPException):
            pass

    @discord.ui.button(
        label="Upvote",
        emoji="👍",
        style=discord.ButtonStyle.success,
    )
    async def upvote(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        await self._vote(
            interaction,
            True,
        )

    @discord.ui.button(
        label="Downvote",
        emoji="👎",
        style=discord.ButtonStyle.danger,
    )
    async def downvote(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        await self._vote(
            interaction,
            False,
        )