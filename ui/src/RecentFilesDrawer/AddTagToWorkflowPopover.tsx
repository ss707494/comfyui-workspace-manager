import {
  Button,
  PopoverTrigger,
  PopoverContent,
  PopoverArrow,
  PopoverCloseButton,
  PopoverBody,
  Popover,
  PopoverHeader,
  Input,
  HStack,
  IconButton,
} from "@chakra-ui/react";
import { useEffect, useState, useContext } from "react";
import { Tag, Workflow, tagsTable, updateFlow } from "../db-tables/WorkspaceDB";
import { IconPlus, IconTag } from "@tabler/icons-react";
import { MultiValue, Select } from "chakra-react-select";
import { RecentFilesContext } from "../WorkspaceContext";

type Props = {
  workflow: Workflow;
};
export default function AddTagToWorkflowPopover({ workflow }: Props) {
  const { onRefreshFilesList } = useContext(RecentFilesContext);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const initialTags =
    workflow.tags?.map((t) => ({
      value: t,
      label: t,
    })) ?? [];
  const [selectedTags, setSelectedTags] =
    useState<MultiValue<{ value: string; label: string }>>(initialTags);
  useEffect(() => {
    tagsTable && setAllTags(tagsTable.listAll() ?? []);
  }, []);
  useEffect(() => {
    setSelectedTags(
      workflow.tags?.map((t) => ({
        value: t,
        label: t,
      })) ?? []
    );
  }, [workflow.tags]);
  if (tagsTable == null) {
    alert("Error: TagsTable is not loaded");
    return null;
  }
  const tagOptions = allTags.map((t) => ({
    value: t.name,
    label: t.name,
  }));
  const maxTagMenuHeight = 37 * 5;

  return (
    <Popover isLazy={true}>
      <PopoverTrigger>
        <IconButton
          aria-label="Delete confirm"
          size={"sm"}
          variant="ghost"
          icon={<IconTag color={"#718096"} />}
        />
      </PopoverTrigger>
      <PopoverContent>
        <PopoverArrow />
        <PopoverCloseButton />
        <PopoverHeader>
          <b>{workflow.name}</b>
        </PopoverHeader>
        <PopoverBody>
          <Select
            isMulti
            name="tags"
            options={tagOptions}
            menuIsOpen={true}
            value={selectedTags}
            onChange={(selected) => {
              setSelectedTags(selected);
              updateFlow(workflow.id, {
                tags: selected.map((s) => s.value),
              });
              onRefreshFilesList && onRefreshFilesList();
            }}
            chakraStyles={{
              dropdownIndicator: (provided, state) => ({
                ...provided,
                p: 0,
                w: "30px",
              }),
              menuList: (provided, state) => ({
                ...provided,
                shadow: "none",
                pt: 0,
              }),
            }}
            placeholder="Select tags"
            closeMenuOnSelect={false}
            maxMenuHeight={maxTagMenuHeight}
          />
          <HStack
            gap={4}
            mt={Math.min(maxTagMenuHeight, Math.max(allTags.length, 3) * 37)}
          >
            <Input
              placeholder="New tag name"
              size="sm"
              mt={6}
              mb={6}
              variant={"flushed"}
              value={newTagName}
              onChange={(e) => {
                setNewTagName(e.target.value);
              }}
            />
            <Button
              iconSpacing={1}
              leftIcon={<IconPlus size={16} />}
              colorScheme="teal"
              variant="solid"
              size={"xs"}
              px={5}
              isDisabled={newTagName.length === 0}
              onClick={() => {
                tagsTable?.upsert(newTagName);
                setAllTags(tagsTable?.listAll() ?? []);
                setNewTagName("");
              }}
            >
              New Tag
            </Button>
          </HStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
}
