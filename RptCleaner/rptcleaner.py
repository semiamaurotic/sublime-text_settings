import sublime
import sublime_plugin
import re
import itertools


def findfaults(lines):
	for i, line in enumerate(lines):
		if 'request' in line or 'failed' in line:
			# if the following unit's rm # ends with "02" use the following rm, 
			# rather than the preceeding rm, as the basis for inference.
			if lines[i+1][9:11]=='02':
				refline = lines[i+1]
				lines[i] = '{}{}{}{}'.format(
					refline[:8], int(refline[8:11]) - 1, refline[11:17], '\tInferred')
			else:
				refline = lines[i-1]
				lines[i] = '{}{}{}{}'.format(
					refline[:8], int(refline[8:11]) + 1, refline[11:17], '\tInferred')

	return lines
		


def tamperdetect(lines):
	tampered = [line[:4] + line[7:] for line in lines if re.match(r'^.+AV_59\t(?!21|71)', line)]
	return tampered


def wingreplace(lines):
	for i, line in enumerate(lines):
		if line.startswith('001'):
			if re.match(r'001\.\d1', line):
				lines[i] = re.sub(r'(\d{3}\.)(\d)(1)(\d{2})', r'\1(\2)A\2\4', line)
			else:
				lines[i] = re.sub(r'(\d{3}\.)(\d)(2)(\d{2})', r'\1(\2)B\2\4', line)
		else:
			lines[i] = re.sub(r'(\d{3}\.)(A|B)(\d)(\d{2})', r'\1(\3)\2\3\4', line)
	return lines


def insightcleaner(content):
	content = re.sub(r' {4,}DEG F', r' DEG F', content)
	content = re.sub(r' {3,}', r'\t', content)
	content = re.sub(r':  No match found\.', r'\tNo match found', content)
	content = re.sub(r'255 255 59\t\(\t\) ' , r'', content)
	lines = [ln for ln in content.splitlines() if re.match(r'^\d+', ln)]
	lines = wingreplace(lines)
	lines = findfaults(lines)
	return lines


def telnetcleaner(content):
	content = re.sub(r'\n\n', r'\n', content)
	content = re.sub(r'\n  :', r':', content)
	content = re.sub(r' {4,}', r'\t', content)
	# Drop lines that start with non-digit characters
	lines = [ln for ln in content.splitlines() if re.match(r'^\d+', ln)]
	lines = wingreplace(lines)
	return lines


class RptcleanerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.settings().set('translate_tabs_to_spaces', False)
		allregion = sublime.Region(0, self.view.size())
		content = self.view.substr(allregion)
		if 'Insight' in content:
			cleaned = insightcleaner(content)
		else:
			cleaned = telnetcleaner(content)
		# faults = findfaults(cleaned)
		tampered = tamperdetect(cleaned)
		output = '{header}\n\nTampered:\n{tampered}\n\nAll:\n{all}'.format(
			header=cleaned[0], tampered='\n'.join(tampered), all='\n'.join(cleaned[1:]))
		self.view.replace(edit, allregion, output)

		self.view.settings().set('tab_size', 1)
		self.view.settings().set('tab_size', 8)
		print('cleaned')
