{{- $page := .page -}}
{{- $data := hugo.Data.community.roster -}}
{{- $labels := dict
  "en" (dict "title" "Project members" "lead" "Current Apache HugeGraph PMC members and Committers, sourced from ASF records. [How to become a HugeGraph Committer](/docs/contribution-guidelines/committer-guidelines/) (Apache nomination and election)" "chair" "Chair")
  "cn" (dict "title" "项目成员" "lead" "Apache HugeGraph 当前的 PMC 成员与 Committers，数据来自 ASF 记录。[如何成为 HugeGraph Committer](/cn/docs/contribution-guidelines/committer-guidelines/)（注：需经阿帕奇提名与选举）" "chair" "主席")
-}}
{{- $copy := index $labels $page.Language.Lang | default (index $labels "en") -}}
## {{ $copy.title }}

{{ $copy.lead }}

{{ range $role := slice "pmc" "committers" -}}
### {{ if eq $role "pmc" }}PMC{{ else }}Committers{{ end }}

{{ range (index $data.roles $role) -}}
{{- $label := .name -}}
{{- $label = partial "content/markdown-escape.html" $label -}}
{{- if .github -}}
{{- $url := partial "content/markdown-url.html" .profile_url -}}
- [{{ $label }}]({{ $url }})
{{- else -}}
- {{ $label }}
{{- end }}
{{ end }}

{{ end -}}
