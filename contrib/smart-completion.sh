#
# Copyright (c) 2005 Canonical
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Mauricio Teixeira <mteixeira@webset.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

_smart() {

    local cur prev opts

    smartdir=$(python -c "import smart; print smart.__file__" \
	           | awk '{sub("/__init__.py[c]?","");print}')
	commands="$(ls ${smartdir}/commands/*.py \
	            | awk -F '/' '{gsub(/\.py|__init__.py[c]?|\n/,""); print $NF}')"

    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ ${prev} == "smart" ]] ; then
        # Completion for general options and action commands
        opts="${commands} $(grep "add_option" $(which smart) | tr \" \\n \
		        | grep "^-" | tr \\n " ")"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    elif [[ ! -z "$(echo $commands | grep ${COMP_WORDS[1]})" ]] ; then
        # Completion for action command options
        opts="$(grep "add_option" "${smartdir}/commands/${COMP_WORDS[1]}.py" \
		        | tr \" \\n | grep "^-" | tr \\n " ")"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
	fi
}

complete -F _smart smart
